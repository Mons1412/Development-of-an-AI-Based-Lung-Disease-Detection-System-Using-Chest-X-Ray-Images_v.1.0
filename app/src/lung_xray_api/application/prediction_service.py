"""Application service điều phối inference.

Service này áp dụng Dependency Injection: validator, preprocessor và predictor
được truyền vào từ composition root. Nhờ đó service không phụ thuộc FastAPI và
có thể unit test bằng fake runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator, ValidatedImage
from lung_xray_api.infrastructure.ml.predictor import Predictor


@dataclass(frozen=True)
class PredictionResult:
    status: str
    prediction: str
    model_probability: float
    probabilities: dict[str, float]
    model_version: str
    processing_time_ms: int
    disclaimer: str

    def to_response(self) -> dict[str, object]:
        response: dict[str, object] = {
            "status": self.status,
            "prediction": self.prediction,
            "model_probability": self.model_probability,
            "probabilities": self.probabilities,
            "model_version": self.model_version,
            "processing_time_ms": self.processing_time_ms,
            "disclaimer": self.disclaimer,
        }
        for class_name, probability in self.probabilities.items():
            response[f"{class_name}_probability"] = probability
        return response


class PredictionBundleProtocol(Protocol):
    @property
    def model_version(self) -> str:
        """Model version dùng bởi health endpoint."""
        ...


class PredictionServiceProtocol(Protocol):
    @property
    def bundle(self) -> PredictionBundleProtocol:
        """Bundle metadata tối thiểu cho health/model version."""
        ...

    def predict_bytes(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> PredictionResult:
        """Phân loại ảnh đã đọc thành bytes."""
        ...

    def model_info(self) -> dict[str, object]:
        """Trả metadata public của model."""
        ...


class PredictionService:
    def __init__(
        self,
        bundle: ArtifactBundle,
        validator: ImageValidator,
        preprocessor: ImagePreprocessor,
        predictor: Predictor,
    ) -> None:
        self.bundle = bundle
        self.validator = validator
        self.preprocessor = preprocessor
        self.predictor = predictor

    def predict_bytes(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> PredictionResult:
        start = perf_counter()
        validated = self.validate_upload(content, filename=filename, content_type=content_type)
        return self._predict_validated(validated, start)

    def validate_upload(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> ValidatedImage:
        """Validate an upload once for the server-bound persisted-analysis flow."""

        return self.validator.validate(content, filename=filename, content_type=content_type)

    def predict_validated_image(self, validated: ValidatedImage) -> PredictionResult:
        """Run the unchanged preprocessing/predictor path for an already validated image."""

        return self._predict_validated(validated, perf_counter())

    def _predict_validated(self, validated: ValidatedImage, start: float) -> PredictionResult:
        batch = self.preprocessor.preprocess(validated)
        output = self.predictor.predict(batch)
        latency_ms = int((perf_counter() - start) * 1000)
        return PredictionResult(
            status="success",
            prediction=output.prediction,
            model_probability=output.model_probability,
            probabilities=output.probabilities,
            model_version=self.bundle.model_version,
            processing_time_ms=latency_ms,
            disclaimer=self.bundle.disclaimer,
        )

    def model_info(self) -> dict[str, object]:
        return {
            "model_name": self.bundle.metadata["model_name"],
            "model_version": self.bundle.model_version,
            "architecture": self.bundle.metadata["architecture"],
            "classes": self.bundle.class_names,
            "input_shape": self.bundle.metadata["input_shape"],
            "preprocessing": self.bundle.preprocessing,
            "metrics": self.bundle.metrics,
            "disclaimer": self.bundle.disclaimer,
        }
