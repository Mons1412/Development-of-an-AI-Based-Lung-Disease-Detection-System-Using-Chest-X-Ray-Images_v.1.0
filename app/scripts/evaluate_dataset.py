"""Evaluate the production Lung X-ray inference contract on folder-labelled images.

The tool is intentionally offline and does not alter weights, retrain the model,
or write anything outside the requested output directory. Folder labels are only
reported as confirmed ground truth when the operator explicitly confirms them.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from lung_xray_api.application.prediction_service import PredictionResult, PredictionServiceProtocol
from lung_xray_api.core.config import load_settings
from lung_xray_api.core.lifespan import build_prediction_service


CLASSES = ("normal", "pneumonia", "tuberculosis")
CONTENT_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
PREDICTION_FIELDS = (
    "dataset_path",
    "ground_truth_class",
    "status",
    "predicted_class",
    "model_probability",
    "normal_probability",
    "pneumonia_probability",
    "tuberculosis_probability",
    "processing_time_ms",
    "model_version",
    "skip_reason",
)
SKIPPED_FIELDS = ("dataset_path", "ground_truth_class", "reason", "detail")
OUTPUT_FILENAMES = (
    "predictions.csv",
    "skipped_files.csv",
    "confusion_matrix.csv",
    "metrics.json",
    "evaluation_summary.json",
)


@dataclass(frozen=True)
class ImageCandidate:
    ground_truth_class: str
    path: Path
    relative_path: str


@dataclass(frozen=True)
class DatasetDiscovery:
    candidates: tuple[ImageCandidate, ...]
    skipped_files: tuple[dict[str, str], ...]
    missing_class_folders: tuple[str, ...]
    empty_class_folders: tuple[str, ...]
    unexpected_top_level_folders: tuple[str, ...]
    selection_method: str


def percentile(values: list[int], quantile: float) -> float | None:
    """Return linear-interpolated percentile without a numerical dependency."""

    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower_index = math.floor(index)
    upper_index = math.ceil(index)
    if lower_index == upper_index:
        return float(ordered[lower_index])
    fraction = index - lower_index
    return ordered[lower_index] * (1.0 - fraction) + ordered[upper_index] * fraction


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def discover_dataset(
    dataset_root: Path,
    *,
    limit_per_class: int | None = None,
    max_samples: int | None = None,
) -> DatasetDiscovery:
    """Discover supported images and record unsupported files without loading a model."""

    dataset_root = dataset_root.resolve()
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Dataset root không tồn tại hoặc không phải thư mục: {dataset_root}")

    if limit_per_class is not None and limit_per_class < 1:
        raise ValueError("limit_per_class phải lớn hơn 0")
    if max_samples is not None and max_samples < 1:
        raise ValueError("max_samples phải lớn hơn 0")

    top_level_folders = {
        item.name for item in dataset_root.iterdir() if item.is_dir() and not item.name.startswith(".")
    }
    unexpected_folders = tuple(sorted(top_level_folders - set(CLASSES)))
    missing_folders: list[str] = []
    empty_folders: list[str] = []
    skipped_files: list[dict[str, str]] = []
    candidates_by_class: dict[str, list[ImageCandidate]] = {class_name: [] for class_name in CLASSES}

    for class_name in CLASSES:
        class_folder = dataset_root / class_name
        if not class_folder.is_dir():
            missing_folders.append(class_name)
            continue

        for image_path in sorted(class_folder.rglob("*"), key=lambda path: path.as_posix().lower()):
            if not image_path.is_file():
                continue
            relative_path = image_path.relative_to(dataset_root).as_posix()
            suffix = image_path.suffix.lower()
            if suffix not in CONTENT_TYPES:
                skipped_files.append(
                    {
                        "dataset_path": relative_path,
                        "ground_truth_class": class_name,
                        "reason": "unsupported_extension",
                        "detail": suffix or "no_extension",
                    }
                )
                continue
            candidates_by_class[class_name].append(
                ImageCandidate(
                    ground_truth_class=class_name,
                    path=image_path,
                    relative_path=relative_path,
                )
            )

        if not candidates_by_class[class_name]:
            empty_folders.append(class_name)

        if limit_per_class is not None:
            candidates_by_class[class_name] = candidates_by_class[class_name][:limit_per_class]

    selected_candidates = _round_robin_select(candidates_by_class, max_samples=max_samples)
    selection_method = "sorted paths, round-robin by class"
    if limit_per_class is not None:
        selection_method += f", limit_per_class={limit_per_class}"
    if max_samples is not None:
        selection_method += f", max_samples={max_samples}"

    return DatasetDiscovery(
        candidates=tuple(selected_candidates),
        skipped_files=tuple(skipped_files),
        missing_class_folders=tuple(missing_folders),
        empty_class_folders=tuple(empty_folders),
        unexpected_top_level_folders=unexpected_folders,
        selection_method=selection_method,
    )


def _round_robin_select(
    candidates_by_class: dict[str, list[ImageCandidate]],
    *,
    max_samples: int | None,
) -> list[ImageCandidate]:
    """Select deterministically without class-order bias when a total limit is used."""

    selected: list[ImageCandidate] = []
    index = 0
    while True:
        selected_this_round = False
        for class_name in CLASSES:
            class_candidates = candidates_by_class[class_name]
            if index >= len(class_candidates):
                continue
            selected.append(class_candidates[index])
            selected_this_round = True
            if max_samples is not None and len(selected) >= max_samples:
                return selected
        if not selected_this_round:
            return selected
        index += 1


def evaluate_candidates(
    candidates: Iterable[ImageCandidate],
    service: PredictionServiceProtocol,
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    """Run a supplied inference service and retain individual failures as skipped rows."""

    prediction_rows: list[dict[str, object]] = []
    skipped_rows: list[dict[str, str]] = []
    fallback_model_version = _service_model_version(service)

    for candidate in candidates:
        try:
            result = service.predict_bytes(
                candidate.path.read_bytes(),
                filename=candidate.path.name,
                content_type=CONTENT_TYPES[candidate.path.suffix.lower()],
            )
            _validate_prediction_result(result)
            prediction_rows.append(_success_row(candidate, result))
        except Exception as error:  # Individual invalid images must not abort an evaluation run.
            reason = type(error).__name__
            detail = str(error) or "Không có thông điệp lỗi"
            prediction_rows.append(
                _skipped_prediction_row(
                    candidate,
                    model_version=fallback_model_version,
                    reason=reason,
                )
            )
            skipped_rows.append(
                {
                    "dataset_path": candidate.relative_path,
                    "ground_truth_class": candidate.ground_truth_class,
                    "reason": reason,
                    "detail": detail,
                }
            )

    return prediction_rows, skipped_rows


def _service_model_version(service: PredictionServiceProtocol) -> str:
    return str(service.bundle.model_version)


def _validate_prediction_result(result: PredictionResult) -> None:
    if result.prediction not in CLASSES:
        raise ValueError(f"Prediction class không thuộc contract: {result.prediction}")
    if set(result.probabilities) != set(CLASSES):
        raise ValueError("Prediction probabilities không có đúng ba class production")
    probability_values = list(result.probabilities.values())
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        for value in probability_values
    ):
        raise ValueError("Prediction probabilities không phải số hữu hạn")
    if any(value < 0.0 or value > 1.0 for value in probability_values):
        raise ValueError("Prediction probabilities nằm ngoài [0, 1]")
    if not math.isclose(sum(probability_values), 1.0, rel_tol=0.0, abs_tol=1e-4):
        raise ValueError("Tổng prediction probabilities không gần 1")
    if not isinstance(result.processing_time_ms, int) or result.processing_time_ms < 0:
        raise ValueError("Processing time không hợp lệ")


def _success_row(candidate: ImageCandidate, result: PredictionResult) -> dict[str, object]:
    return {
        "dataset_path": candidate.relative_path,
        "ground_truth_class": candidate.ground_truth_class,
        "status": "success",
        "predicted_class": result.prediction,
        "model_probability": result.model_probability,
        "normal_probability": result.probabilities["normal"],
        "pneumonia_probability": result.probabilities["pneumonia"],
        "tuberculosis_probability": result.probabilities["tuberculosis"],
        "processing_time_ms": result.processing_time_ms,
        "model_version": result.model_version,
        "skip_reason": "",
    }


def _skipped_prediction_row(
    candidate: ImageCandidate,
    *,
    model_version: str,
    reason: str,
) -> dict[str, object]:
    return {
        "dataset_path": candidate.relative_path,
        "ground_truth_class": candidate.ground_truth_class,
        "status": "skipped",
        "predicted_class": "",
        "model_probability": "",
        "normal_probability": "",
        "pneumonia_probability": "",
        "tuberculosis_probability": "",
        "processing_time_ms": "",
        "model_version": model_version,
        "skip_reason": reason,
    }


def calculate_metrics(prediction_rows: Iterable[dict[str, object]]) -> dict[str, object]:
    """Calculate folder-label metrics for successful, contract-valid predictions only."""

    matrix = {truth: {predicted: 0 for predicted in CLASSES} for truth in CLASSES}
    latencies: list[int] = []
    skipped_count = 0

    for row in prediction_rows:
        if row["status"] != "success":
            skipped_count += 1
            continue
        truth = str(row["ground_truth_class"])
        predicted = str(row["predicted_class"])
        if truth not in CLASSES or predicted not in CLASSES:
            raise ValueError("Prediction row không tuân theo class contract")
        processing_time_ms = row["processing_time_ms"]
        if not isinstance(processing_time_ms, int) or isinstance(processing_time_ms, bool):
            raise ValueError("Prediction row có processing_time_ms không hợp lệ")
        matrix[truth][predicted] += 1
        latencies.append(processing_time_ms)

    total_successful = sum(sum(row.values()) for row in matrix.values())
    correct = sum(matrix[class_name][class_name] for class_name in CLASSES)
    supports: dict[str, int] = {}
    per_class: dict[str, dict[str, float | int]] = {}

    for class_name in CLASSES:
        true_positive = matrix[class_name][class_name]
        false_positive = sum(
            matrix[truth][class_name] for truth in CLASSES if truth != class_name
        )
        false_negative = sum(
            matrix[class_name][predicted] for predicted in CLASSES if predicted != class_name
        )
        support = sum(matrix[class_name].values())
        precision = safe_divide(true_positive, true_positive + false_positive)
        recall = safe_divide(true_positive, true_positive + false_negative)
        f1 = safe_divide(2 * precision * recall, precision + recall)
        supports[class_name] = support
        per_class[class_name] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }

    macro_precision = statistics.fmean(per_class[class_name]["precision"] for class_name in CLASSES)
    macro_recall = statistics.fmean(per_class[class_name]["recall"] for class_name in CLASSES)
    macro_f1 = statistics.fmean(per_class[class_name]["f1"] for class_name in CLASSES)
    weighted_precision = safe_divide(
        sum(float(per_class[class_name]["precision"]) * supports[class_name] for class_name in CLASSES),
        total_successful,
    )
    weighted_recall = safe_divide(
        sum(float(per_class[class_name]["recall"]) * supports[class_name] for class_name in CLASSES),
        total_successful,
    )
    weighted_f1 = safe_divide(
        sum(float(per_class[class_name]["f1"]) * supports[class_name] for class_name in CLASSES),
        total_successful,
    )

    return {
        "total_successful": total_successful,
        "total_skipped": skipped_count,
        "folder_label_accuracy": safe_divide(correct, total_successful) if total_successful else None,
        "per_class": per_class,
        "macro": {
            "precision": macro_precision,
            "recall": macro_recall,
            "f1": macro_f1,
        },
        "weighted": {
            "precision": weighted_precision,
            "recall": weighted_recall,
            "f1": weighted_f1,
        },
        "confusion_matrix": matrix,
        "latency_ms": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "median": statistics.median(latencies) if latencies else None,
            "p95": percentile(latencies, 0.95),
        },
    }


def build_warnings(
    discovery: DatasetDiscovery,
    *,
    low_sample_threshold: int,
    ground_truth_confirmed: bool,
    training_overlap_reviewed: bool,
    dataset_source: str,
) -> list[str]:
    warnings: list[str] = []
    if discovery.missing_class_folders:
        warnings.append(
            "Thiếu class folder mong đợi: " + ", ".join(discovery.missing_class_folders)
        )
    if discovery.empty_class_folders:
        warnings.append(
            "Class folder không có ảnh JPG/JPEG/PNG hỗ trợ: "
            + ", ".join(discovery.empty_class_folders)
        )
    if discovery.unexpected_top_level_folders:
        warnings.append(
            "Bỏ qua top-level folder không thuộc class contract: "
            + ", ".join(discovery.unexpected_top_level_folders)
        )
    if not discovery.candidates:
        warnings.append("Dataset rỗng: không tìm thấy ảnh JPG/JPEG/PNG để đánh giá.")
    if len(discovery.candidates) < low_sample_threshold:
        warnings.append(
            f"Số mẫu được chọn rất thấp ({len(discovery.candidates)} < {low_sample_threshold})."
        )
    if not ground_truth_confirmed:
        warnings.append(
            "Ground truth chưa được xác nhận độc lập; chỉ diễn giải kết quả như folder-label metrics, "
            "không tuyên bố accuracy đã được xác thực."
        )
    if not training_overlap_reviewed:
        warnings.append(
            "Chưa kiểm tra overlap với training set; không dùng kết quả này để tuyên bố held-out accuracy."
        )
    if dataset_source == "not_provided":
        warnings.append("Dataset source chưa được cung cấp trong metadata run.")
    return warnings


def write_evaluation_outputs(
    output_dir: Path,
    *,
    prediction_rows: list[dict[str, object]],
    skipped_rows: list[dict[str, str]],
    metrics: dict[str, object],
    summary: dict[str, object],
) -> None:
    """Write only well-known evaluation artifacts to the requested output directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "predictions.csv", PREDICTION_FIELDS, prediction_rows)
    _write_csv(output_dir / "skipped_files.csv", SKIPPED_FIELDS, skipped_rows)
    _write_confusion_matrix(output_dir / "confusion_matrix.csv", metrics["confusion_matrix"])
    _write_json(output_dir / "metrics.json", metrics)
    _write_json(output_dir / "evaluation_summary.json", summary)


def _write_csv(
    destination: Path,
    fieldnames: tuple[str, ...],
    rows: Iterable[dict[str, Any]],
) -> None:
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_confusion_matrix(destination: Path, matrix: object) -> None:
    if not isinstance(matrix, dict):
        raise ValueError("Confusion matrix không hợp lệ")
    with destination.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(("ground_truth_class", *CLASSES))
        for truth in CLASSES:
            row = matrix.get(truth)
            if not isinstance(row, dict):
                raise ValueError("Confusion matrix không hợp lệ")
            writer.writerow((truth, *(row.get(predicted, 0) for predicted in CLASSES)))


def _write_json(destination: Path, payload: dict[str, object]) -> None:
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_output_directory_is_safe(output_dir: Path, dataset_root: Path, *, overwrite: bool) -> None:
    resolved_output = output_dir.resolve()
    resolved_dataset = dataset_root.resolve()
    if resolved_output.is_relative_to(resolved_dataset):
        raise ValueError("output_dir không được nằm trong dataset_root")
    existing_outputs = [name for name in OUTPUT_FILENAMES if (resolved_output / name).exists()]
    if existing_outputs and not overwrite:
        raise FileExistsError(
            "Output đã tồn tại; dùng --overwrite nếu chủ động thay thế: " + ", ".join(existing_outputs)
        )


def build_summary(
    *,
    dataset_root: Path,
    dataset_id: str,
    dataset_source: str,
    discovery: DatasetDiscovery,
    metrics: dict[str, object],
    skipped_rows: list[dict[str, str]],
    model_version: str | None,
    ground_truth_confirmed: bool,
    training_overlap_reviewed: bool,
    warnings: list[str],
) -> dict[str, object]:
    skipped_by_reason = Counter(row["reason"] for row in skipped_rows)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_id": dataset_id,
        "dataset_source": dataset_source,
        "dataset_root_name": dataset_root.name,
        "selection_method": discovery.selection_method,
        "model_version": model_version,
        "ground_truth_status": "confirmed" if ground_truth_confirmed else "unconfirmed_folder_labels",
        "training_overlap_reviewed": training_overlap_reviewed,
        "environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "counts": {
            "selected_supported_images": len(discovery.candidates),
            "unsupported_files": len(discovery.skipped_files),
            "inference_skipped_files": len(skipped_rows) - len(discovery.skipped_files),
            "skipped_by_reason": dict(sorted(skipped_by_reason.items())),
        },
        "warnings": warnings,
        "metrics": metrics,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the production Lung X-ray model on folder-labelled local images."
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-id", type=str)
    parser.add_argument("--dataset-source", type=str, default="not_provided")
    parser.add_argument("--limit-per-class", type=int)
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--low-sample-threshold", type=int, default=30)
    parser.add_argument("--ground-truth-confirmed", action="store_true")
    parser.add_argument("--training-overlap-reviewed", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.low_sample_threshold < 1:
        raise ValueError("low_sample_threshold phải lớn hơn 0")

    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    ensure_output_directory_is_safe(output_dir, dataset_root, overwrite=args.overwrite)
    discovery = discover_dataset(
        dataset_root,
        limit_per_class=args.limit_per_class,
        max_samples=args.max_samples,
    )
    warnings = build_warnings(
        discovery,
        low_sample_threshold=args.low_sample_threshold,
        ground_truth_confirmed=args.ground_truth_confirmed,
        training_overlap_reviewed=args.training_overlap_reviewed,
        dataset_source=args.dataset_source,
    )
    skipped_rows = list(discovery.skipped_files)
    prediction_rows: list[dict[str, object]] = []
    model_version: str | None = None

    if discovery.candidates:
        settings = load_settings()
        service, runtime = build_prediction_service(settings, warm_up=True)
        model_version = _service_model_version(service)
        try:
            prediction_rows, inference_skipped_rows = evaluate_candidates(discovery.candidates, service)
            skipped_rows.extend(inference_skipped_rows)
        finally:
            runtime.close()

    metrics = calculate_metrics(prediction_rows)
    metrics["accuracy"] = (
        metrics["folder_label_accuracy"] if args.ground_truth_confirmed else None
    )
    metrics["accuracy_status"] = (
        "confirmed_ground_truth"
        if args.ground_truth_confirmed
        else "not_reported_until_ground_truth_is_confirmed"
    )
    summary = build_summary(
        dataset_root=dataset_root,
        dataset_id=args.dataset_id or dataset_root.name,
        dataset_source=args.dataset_source,
        discovery=discovery,
        metrics=metrics,
        skipped_rows=skipped_rows,
        model_version=model_version,
        ground_truth_confirmed=args.ground_truth_confirmed,
        training_overlap_reviewed=args.training_overlap_reviewed,
        warnings=warnings,
    )
    write_evaluation_outputs(
        output_dir,
        prediction_rows=prediction_rows,
        skipped_rows=skipped_rows,
        metrics=metrics,
        summary=summary,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if discovery.candidates else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError, ValueError) as error:
        print(f"EVALUATION_ERROR: {error}", file=sys.stderr)
        raise SystemExit(2) from error
