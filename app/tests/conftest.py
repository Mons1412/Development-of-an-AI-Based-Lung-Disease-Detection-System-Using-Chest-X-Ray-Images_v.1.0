from __future__ import annotations

from dataclasses import dataclass, replace
from io import BytesIO

import pytest
from PIL import Image

from lung_xray_api.application.prediction_service import PredictionResult
from lung_xray_api.core.config import load_settings
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.main import create_app


def make_image_bytes(format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), color=(128, 128, 128)).save(buffer, format=format)
    return buffer.getvalue()


@dataclass(frozen=True)
class FakeBundle:
    model_version: str = "1.1.0"
    class_names: tuple[str, str, str] = ("normal", "pneumonia", "tuberculosis")


class FakePredictionService:
    def __init__(self) -> None:
        self.bundle = FakeBundle()
        self.validator = ImageValidator(max_upload_bytes=1024 * 1024)

    def predict_bytes(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> PredictionResult:
        validated = self.validate_upload(content, filename=filename, content_type=content_type)
        return self.predict_validated_image(validated)

    def validate_upload(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ):
        return self.validator.validate(content, filename=filename, content_type=content_type)

    def predict_validated_image(self, validated_image) -> PredictionResult:
        return PredictionResult(
            status="success",
            prediction="pneumonia",
            model_probability=0.8,
            probabilities={"normal": 0.1, "pneumonia": 0.8, "tuberculosis": 0.1},
            model_version="1.1.0",
            processing_time_ms=1,
            disclaimer="Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.",
        )

    def model_info(self) -> dict[str, object]:
        return {
            "model_name": "lung_classifier",
            "model_version": "1.1.0",
            "architecture": "MobileNetV2 Transfer Learning",
            "classes": list(self.bundle.class_names),
            "input_shape": [224, 224, 3],
            "preprocessing": {"preprocessing_location": "embedded_in_model"},
            "metrics": {"accuracy": 0.8962264150943396},
            "disclaimer": "Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.",
        }


@pytest.fixture
def artifact_dir():
    path = __import__("pathlib").Path("artifacts/lung_classifier/1.1.0").resolve()
    required = {
        "lung_classifier_v1.keras",
        "class_indices.json",
        "preprocessing_config.json",
        "model_metadata.json",
        "inference_contract.json",
        "metrics.json",
        "model_runtime_requirements.txt",
        "checksums.json",
    }
    if any(not (path / name).is_file() for name in required):
        pytest.skip("Real model artifacts were intentionally excluded from the source-review bundle")
    return path


@pytest.fixture
def test_settings(tmp_path):
    return replace(
        load_settings(),
        app_env="test",
        online_ai_enabled=False,
        gemini_api_key=None,
        history_db_path=tmp_path / "data" / "lung_xray_history.db",
        thumbnail_dir=tmp_path / "data" / "thumbnails",
    )


@pytest.fixture
def test_client(test_settings):
    from fastapi.testclient import TestClient

    app = create_app(settings=test_settings, prediction_service=FakePredictionService())
    with TestClient(app) as client:
        yield client
