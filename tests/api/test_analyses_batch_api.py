from __future__ import annotations

import importlib
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient


analyses_api = importlib.import_module(
    "lung_xray_api.api.v1.analyses"
)


def override_get_db():
    yield object()


def override_require_user():
    return SimpleNamespace(
        id=1,
        role="USER",
    )


def make_client() -> TestClient:
    app = FastAPI()

    app.include_router(
        analyses_api.router
    )

    app.dependency_overrides[
        analyses_api.get_db
    ] = override_get_db

    app.dependency_overrides[
        analyses_api.require_user
    ] = override_require_user

    return TestClient(app)


def test_batch_accepts_multiple_files(
    monkeypatch,
):
    client = make_client()

    captured = {}

    def fake_analyze_images(
        self,
        db,
        current_user,
        *,
        images,
        model_id,
    ):
        captured["images"] = images
        captured["model_id"] = model_id
        captured["user"] = current_user

        return {
            "total": len(images),
            "completed": 0,
            "rejected": len(images),
            "failed": 0,
            "items": [
                {
                    "filename": (
                        image.original_filename
                    ),
                    "status": "REJECTED",
                    "analysis": None,
                    "error": "Test rejection.",
                }
                for image in images
            ],
        }

    monkeypatch.setattr(
        type(
            analyses_api
            .batch_analysis_service
        ),
        "analyze_images",
        fake_analyze_images,
    )

    response = client.post(
        "/api/v1/analyses/batch",
        files=[
            (
                "files",
                (
                    "chest1.jpg",
                    b"image-one",
                    "image/jpeg",
                ),
            ),
            (
                "files",
                (
                    "cat.jpg",
                    b"image-two",
                    "image/jpeg",
                ),
            ),
            (
                "files",
                (
                    "chest2.jpg",
                    b"image-three",
                    "image/jpeg",
                ),
            ),
        ],
        data={
            "model_id": "1",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 3
    assert body["rejected"] == 3

    assert captured["model_id"] == 1

    assert len(
        captured["images"]
    ) == 3

    assert (
        captured["images"][0]
        .original_filename
        == "chest1.jpg"
    )

    assert (
        captured["images"][1]
        .original_filename
        == "cat.jpg"
    )

    assert (
        captured["images"][2]
        .original_filename
        == "chest2.jpg"
    )


def test_batch_requires_files():
    client = make_client()

    response = client.post(
        "/api/v1/analyses/batch",
        data={
            "model_id": "1",
        },
    )

    assert response.status_code == 422


def test_batch_rejects_too_many_files():
    client = make_client()

    files = [
        (
            "files",
            (
                f"image_{index}.jpg",
                b"x",
                "image/jpeg",
            ),
        )
        for index in range(
            analyses_api.MAX_BATCH_FILES + 1
        )
    ]

    response = client.post(
        "/api/v1/analyses/batch",
        files=files,
        data={
            "model_id": "1",
        },
    )

    assert response.status_code == 400

    assert (
        "Too many files"
        in response.json()["detail"]
    )


def test_batch_rejects_total_size_over_limit(
    monkeypatch,
):
    client = make_client()

    monkeypatch.setattr(
        analyses_api,
        "MAX_BATCH_TOTAL_BYTES",
        5,
    )

    response = client.post(
        "/api/v1/analyses/batch",
        files=[
            (
                "files",
                (
                    "image1.jpg",
                    b"abc",
                    "image/jpeg",
                ),
            ),
            (
                "files",
                (
                    "image2.jpg",
                    b"def",
                    "image/jpeg",
                ),
            ),
        ],
        data={
            "model_id": "1",
        },
    )

    assert response.status_code == 413

    assert (
        "Batch size is too large"
        in response.json()["detail"]
    )


def test_batch_maps_lookup_error_to_404(
    monkeypatch,
):
    client = make_client()

    def fake_analyze_images(
        self,
        db,
        current_user,
        *,
        images,
        model_id,
    ):
        raise LookupError(
            "Patient profile not found."
        )

    monkeypatch.setattr(
        type(
            analyses_api
            .batch_analysis_service
        ),
        "analyze_images",
        fake_analyze_images,
    )

    response = client.post(
        "/api/v1/analyses/batch",
        files=[
            (
                "files",
                (
                    "chest.jpg",
                    b"image-data",
                    "image/jpeg",
                ),
            ),
        ],
        data={
            "model_id": "1",
        },
    )

    assert response.status_code == 404

    assert (
        response.json()["detail"]
        == "Patient profile not found."
    )