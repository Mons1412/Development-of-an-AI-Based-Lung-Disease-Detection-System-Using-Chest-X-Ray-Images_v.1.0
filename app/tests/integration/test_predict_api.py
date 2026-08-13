from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lung_xray_api.core.config import load_settings
from lung_xray_api.main import create_app
from tests.conftest import FakePredictionService, make_image_bytes


REQUIRED_SUCCESS_FIELDS = {
    "status",
    "prediction",
    "model_probability",
    "normal_probability",
    "pneumonia_probability",
    "tuberculosis_probability",
    "model_version",
    "processing_time_ms",
    "disclaimer",
}
ALLOWED_CLASSES = {"normal", "pneumonia", "tuberculosis"}


@pytest.fixture(scope="module")
def predict_client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    data_root = tmp_path_factory.mktemp("prediction_api_history") / "data"
    settings = replace(
        load_settings(),
        app_env="test",
        history_db_path=data_root / "lung_xray_history.db",
        thumbnail_dir=data_root / "thumbnails",
    )
    app = create_app(settings=settings, prediction_service=FakePredictionService())
    with TestClient(app) as client:
        yield client


def _post_predict(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    content_type: str,
    field_name: str = "file",
):
    return client.post(
        "/api/v1/predict",
        files={field_name: (filename, content, content_type)},
    )


def _assert_invalid_image(payload: dict[str, Any]) -> None:
    assert payload["status"] == "error"
    assert payload["code"] == "invalid_image"
    assert isinstance(payload["message"], str)
    assert payload["message"]


def _is_json_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def test_predict_accepts_jpeg_with_standard_mime(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.jpg",
        content=make_image_bytes("JPEG"),
        content_type="image/jpeg",
    )

    assert response.status_code == 200
    assert response.json()["prediction"] == "pneumonia"


def test_predict_accepts_png_with_standard_mime(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.png",
        content=make_image_bytes("PNG"),
        content_type="image/png",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_predict_accepts_jpeg_with_mendix_octet_stream(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.jpg",
        content=make_image_bytes("JPEG"),
        content_type="application/octet-stream",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_predict_accepts_png_with_mendix_octet_stream(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.png",
        content=make_image_bytes("PNG"),
        content_type="application/octet-stream",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_predict_rejects_invalid_binary_octet_stream(predict_client):
    response = _post_predict(
        predict_client,
        filename="fake.jpg",
        content=b"not an image",
        content_type="application/octet-stream",
    )

    assert response.status_code == 400
    _assert_invalid_image(response.json())


def test_predict_rejects_empty_file(predict_client):
    response = _post_predict(
        predict_client,
        filename="empty.jpg",
        content=b"",
        content_type="image/jpeg",
    )

    assert response.status_code == 400
    _assert_invalid_image(response.json())


def test_predict_rejects_oversized_file(predict_client):
    response = _post_predict(
        predict_client,
        filename="too-large.jpg",
        content=b"\xff\xd8\xff" + (b"0" * (1024 * 1024 + 1)),
        content_type="image/jpeg",
    )

    assert response.status_code == 400
    _assert_invalid_image(response.json())


def test_predict_rejects_wrong_extension(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.gif",
        content=make_image_bytes("JPEG"),
        content_type="image/jpeg",
    )

    assert response.status_code == 400
    _assert_invalid_image(response.json())


def test_predict_requires_field_named_file(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.jpg",
        content=make_image_bytes("JPEG"),
        content_type="image/jpeg",
        field_name="image",
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_predict_success_response_contract(predict_client):
    response = _post_predict(
        predict_client,
        filename="xray.jpg",
        content=make_image_bytes("JPEG"),
        content_type="application/octet-stream",
    )

    assert response.status_code == 200
    payload = response.json()
    assert REQUIRED_SUCCESS_FIELDS.issubset(payload.keys())
    assert payload["status"] == "success"
    assert isinstance(payload["prediction"], str)
    assert payload["prediction"] in ALLOWED_CLASSES
    assert isinstance(payload["model_version"], str)
    assert payload["model_version"]
    assert isinstance(payload["processing_time_ms"], int)
    assert not isinstance(payload["processing_time_ms"], bool)
    assert payload["processing_time_ms"] >= 0
    assert isinstance(payload["disclaimer"], str)
    assert payload["disclaimer"]

    probability_fields = [
        "model_probability",
        "normal_probability",
        "pneumonia_probability",
        "tuberculosis_probability",
    ]
    for field in probability_fields:
        assert _is_json_number(payload[field])
        assert 0.0 <= payload[field] <= 1.0

    class_probability_sum = (
        payload["normal_probability"]
        + payload["pneumonia_probability"]
        + payload["tuberculosis_probability"]
    )
    assert class_probability_sum == pytest.approx(1.0, abs=1e-6)


def test_predict_compatibility_alias(predict_client):
    response = predict_client.post(
        "/predict",
        files={"file": ("sample.jpg", make_image_bytes("JPEG"), "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_predict_returns_503_when_model_not_ready(tmp_path):
    data_root = tmp_path / "data"
    settings = replace(
        load_settings(),
        app_env="test",
        history_db_path=data_root / "lung_xray_history.db",
        thumbnail_dir=data_root / "thumbnails",
    )
    app = create_app(settings=settings, load_model=False)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/predict",
            files={"file": ("sample.jpg", make_image_bytes("JPEG"), "image/jpeg")},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "Model service chưa ready"
