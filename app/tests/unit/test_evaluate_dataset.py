"""Tests for offline evaluation tooling without loading TensorFlow or model artifacts."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from lung_xray_api.application.prediction_service import PredictionResult
from scripts import evaluate_dataset as evaluator


@dataclass(frozen=True)
class FakeBundle:
    model_version: str = "1.1.0"


class FakePredictionService:
    def __init__(self) -> None:
        self.bundle = FakeBundle()

    def predict_bytes(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> PredictionResult:
        if filename == "invalid.png":
            raise ValueError("Không decode được ảnh")

        prediction = "normal" if filename == "normal.png" else "tuberculosis"
        probabilities = {
            "normal": 0.8 if prediction == "normal" else 0.1,
            "pneumonia": 0.1,
            "tuberculosis": 0.1 if prediction == "normal" else 0.8,
        }
        return PredictionResult(
            status="success",
            prediction=prediction,
            model_probability=probabilities[prediction],
            probabilities=probabilities,
            model_version="1.1.0",
            processing_time_ms=12,
            disclaimer="Học thuật.",
        )

    def model_info(self) -> dict[str, object]:
        return {"model_version": self.bundle.model_version}


class FakeRuntime:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _write_dataset_file(root: Path, class_name: str, filename: str) -> Path:
    destination = root / class_name / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"fixture")
    return destination


def test_discover_dataset_validates_folders_records_unsupported_and_selects_round_robin(
    tmp_path: Path,
) -> None:
    _write_dataset_file(tmp_path, "normal", "a.png")
    _write_dataset_file(tmp_path, "normal", "b.png")
    _write_dataset_file(tmp_path, "normal", "notes.txt")
    _write_dataset_file(tmp_path, "pneumonia", "c.jpg")
    _write_dataset_file(tmp_path, "tuberculosis", "d.jpeg")
    _write_dataset_file(tmp_path, "unexpected", "ignored.png")

    discovery = evaluator.discover_dataset(tmp_path, max_samples=3)

    assert [candidate.relative_path for candidate in discovery.candidates] == [
        "normal/a.png",
        "pneumonia/c.jpg",
        "tuberculosis/d.jpeg",
    ]
    assert discovery.missing_class_folders == ()
    assert discovery.unexpected_top_level_folders == ("unexpected",)
    assert discovery.skipped_files == (
        {
            "dataset_path": "normal/notes.txt",
            "ground_truth_class": "normal",
            "reason": "unsupported_extension",
            "detail": ".txt",
        },
    )


def test_metrics_include_per_class_macro_weighted_confusion_and_latency() -> None:
    rows = [
        {
            "ground_truth_class": "normal",
            "status": "success",
            "predicted_class": "normal",
            "processing_time_ms": 10,
        },
        {
            "ground_truth_class": "pneumonia",
            "status": "success",
            "predicted_class": "normal",
            "processing_time_ms": 20,
        },
        {
            "ground_truth_class": "tuberculosis",
            "status": "success",
            "predicted_class": "tuberculosis",
            "processing_time_ms": 30,
        },
        {"status": "skipped"},
    ]

    metrics = evaluator.calculate_metrics(rows)
    per_class = cast(dict[str, dict[str, float]], metrics["per_class"])
    macro = cast(dict[str, float], metrics["macro"])
    weighted = cast(dict[str, float], metrics["weighted"])
    matrix = cast(dict[str, dict[str, int]], metrics["confusion_matrix"])
    latency = cast(dict[str, float], metrics["latency_ms"])

    assert metrics["total_successful"] == 3
    assert metrics["total_skipped"] == 1
    assert metrics["folder_label_accuracy"] == pytest.approx(2 / 3)
    assert per_class["normal"]["precision"] == pytest.approx(0.5)
    assert per_class["pneumonia"]["recall"] == 0.0
    assert macro["f1"] == pytest.approx((2 / 3 + 0 + 1) / 3)
    assert weighted["f1"] == pytest.approx((2 / 3 + 0 + 1) / 3)
    assert matrix["pneumonia"]["normal"] == 1
    assert latency == {"mean": 20.0, "median": 20, "p95": 29.0}


def test_evaluate_candidates_and_outputs_report_invalid_images_without_tensorflow(
    tmp_path: Path,
) -> None:
    _write_dataset_file(tmp_path, "normal", "normal.png")
    _write_dataset_file(tmp_path, "pneumonia", "invalid.png")
    _write_dataset_file(tmp_path, "tuberculosis", "tuberculosis.png")
    discovery = evaluator.discover_dataset(tmp_path)

    prediction_rows, inference_skipped = evaluator.evaluate_candidates(
        discovery.candidates,
        FakePredictionService(),
    )
    all_skipped = [*discovery.skipped_files, *inference_skipped]
    metrics = evaluator.calculate_metrics(prediction_rows)
    warnings = evaluator.build_warnings(
        discovery,
        low_sample_threshold=10,
        ground_truth_confirmed=False,
        training_overlap_reviewed=False,
        dataset_source="not_provided",
    )
    summary = evaluator.build_summary(
        dataset_root=tmp_path,
        dataset_id="fixture-eval",
        dataset_source="not_provided",
        discovery=discovery,
        metrics=metrics,
        skipped_rows=all_skipped,
        model_version="1.1.0",
        ground_truth_confirmed=False,
        training_overlap_reviewed=False,
        warnings=warnings,
    )
    output_dir = tmp_path.parent / "evaluation-output"

    evaluator.write_evaluation_outputs(
        output_dir,
        prediction_rows=prediction_rows,
        skipped_rows=all_skipped,
        metrics=metrics,
        summary=summary,
    )

    with (output_dir / "predictions.csv").open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert [row["status"] for row in csv_rows] == ["success", "skipped", "success"]
    assert csv_rows[1]["skip_reason"] == "ValueError"
    assert (output_dir / "skipped_files.csv").read_text(encoding="utf-8-sig").count("invalid.png") == 1
    assert (output_dir / "confusion_matrix.csv").read_text(encoding="utf-8-sig").startswith(
        "ground_truth_class,normal,pneumonia,tuberculosis"
    )
    saved_summary = json.loads((output_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert saved_summary["ground_truth_status"] == "unconfirmed_folder_labels"
    assert any("Ground truth" in warning for warning in saved_summary["warnings"])


def test_empty_dataset_creates_warning_outputs_without_loading_a_model(tmp_path: Path) -> None:
    for class_name in evaluator.CLASSES:
        (tmp_path / "dataset" / class_name).mkdir(parents=True)
    output_dir = tmp_path / "output"

    exit_code = evaluator.main(
        [
            "--dataset-root",
            str(tmp_path / "dataset"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 2
    summary = json.loads((output_dir / "evaluation_summary.json").read_text(encoding="utf-8"))
    assert summary["metrics"]["folder_label_accuracy"] is None
    assert summary["metrics"]["accuracy"] is None
    assert any("Dataset rỗng" in warning for warning in summary["warnings"])


def test_main_reports_accuracy_only_after_ground_truth_is_explicitly_confirmed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for class_name in evaluator.CLASSES:
        _write_dataset_file(tmp_path / "dataset", class_name, f"{class_name}.png")
    output_dir = tmp_path / "output"
    runtime = FakeRuntime()

    monkeypatch.setattr(evaluator, "load_settings", lambda: object())
    monkeypatch.setattr(
        evaluator,
        "build_prediction_service",
        lambda settings, warm_up: (FakePredictionService(), runtime),
    )

    exit_code = evaluator.main(
        [
            "--dataset-root",
            str(tmp_path / "dataset"),
            "--output-dir",
            str(output_dir),
            "--ground-truth-confirmed",
            "--training-overlap-reviewed",
            "--dataset-source",
            "verified-fixture",
        ]
    )

    assert exit_code == 0
    assert runtime.closed is True
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["accuracy"] == pytest.approx(2 / 3)
    assert metrics["accuracy_status"] == "confirmed_ground_truth"
