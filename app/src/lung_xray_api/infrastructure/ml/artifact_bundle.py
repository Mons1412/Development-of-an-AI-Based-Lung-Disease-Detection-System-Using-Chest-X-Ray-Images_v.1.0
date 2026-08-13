"""Load và validate model artifact bundle.

Artifact bundle là single source of truth cho class order, preprocessing,
metrics và inference contract. Validation fail-fast trước khi load model để
tránh API chạy với metadata và weights không cùng version.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lung_xray_api.core.exceptions import ArtifactError
from lung_xray_api.infrastructure.ml.checksum_verifier import verify_checksums

REQUIRED_FILES = (
    "lung_classifier_v1.keras",
    "class_indices.json",
    "preprocessing_config.json",
    "model_metadata.json",
    "inference_contract.json",
    "metrics.json",
    "model_runtime_requirements.txt",
    "checksums.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ArtifactError(f"Không đọc được artifact JSON: {path}") from error
    except json.JSONDecodeError as error:
        raise ArtifactError(f"Artifact JSON không hợp lệ: {path}") from error
    if not isinstance(payload, dict):
        raise ArtifactError(f"Artifact JSON phải là object: {path.name}")
    return payload


@dataclass(frozen=True)
class ArtifactBundle:
    artifact_dir: Path
    model_path: Path
    class_indices: dict[str, Any]
    preprocessing: dict[str, Any]
    metadata: dict[str, Any]
    inference_contract: dict[str, Any]
    metrics: dict[str, Any]

    @property
    def class_names(self) -> list[str]:
        return list(self.class_indices["class_names"])

    @property
    def model_version(self) -> str:
        return str(self.metadata["model_version"])

    @property
    def disclaimer(self) -> str:
        return str(self.inference_contract["disclaimer"])

    @property
    def input_size(self) -> tuple[int, int]:
        return (
            int(self.preprocessing["input_height"]),
            int(self.preprocessing["input_width"]),
        )

    @classmethod
    def load(cls, artifact_dir: Path, verify_checksum: bool = True) -> "ArtifactBundle":
        artifact_dir = artifact_dir.resolve()
        missing = [name for name in REQUIRED_FILES if not (artifact_dir / name).is_file()]
        if missing:
            raise ArtifactError(f"Artifact bundle thiếu file: {missing}")

        if verify_checksum:
            verify_checksums(artifact_dir)

        class_indices = _read_json(artifact_dir / "class_indices.json")
        preprocessing = _read_json(artifact_dir / "preprocessing_config.json")
        metadata = _read_json(artifact_dir / "model_metadata.json")
        inference_contract = _read_json(artifact_dir / "inference_contract.json")
        metrics = _read_json(artifact_dir / "metrics.json")

        bundle = cls(
            artifact_dir=artifact_dir,
            model_path=artifact_dir / "lung_classifier_v1.keras",
            class_indices=class_indices,
            preprocessing=preprocessing,
            metadata=metadata,
            inference_contract=inference_contract,
            metrics=metrics,
        )
        bundle.validate_contract()
        return bundle

    def validate_contract(self) -> None:
        expected_classes = ["normal", "pneumonia", "tuberculosis"]
        if self.class_names != expected_classes:
            raise ArtifactError(f"Class order sai: {self.class_names}")

        index_to_class = self.class_indices.get("index_to_class", {})
        if [index_to_class.get(str(index)) for index in range(3)] != expected_classes:
            raise ArtifactError("index_to_class không khớp class order")

        if self.metadata.get("model_version") != "1.1.0":
            raise ArtifactError("Model version phải là 1.1.0")

        if self.metadata.get("classes") != expected_classes:
            raise ArtifactError("model_metadata.classes không khớp class order")

        if self.preprocessing.get("preprocessing_location") != "embedded_in_model":
            raise ArtifactError("Preprocessing phải được nhúng trong model")

        if self.preprocessing.get("embedded_layer") != "Rescaling(scale=1/127.5, offset=-1)":
            raise ArtifactError("Embedded preprocessing layer không khớp contract")

        input_shape = self.metadata.get("input_shape")
        if input_shape != [224, 224, 3]:
            raise ArtifactError(f"Input shape sai: {input_shape}")

        if self.inference_contract.get("probability_order") != expected_classes:
            raise ArtifactError("inference_contract probability_order không khớp")

        if self.inference_contract.get("uncertain_threshold") is not None:
            raise ArtifactError("Không được tự thêm uncertain_threshold")
