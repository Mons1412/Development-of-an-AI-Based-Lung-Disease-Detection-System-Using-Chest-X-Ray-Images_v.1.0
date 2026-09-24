from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest


batch_module = importlib.import_module(
    "lung_xray_api.application.services."
    "batch_analysis_service"
)

BatchAnalysisService = (
    batch_module.BatchAnalysisService
)

BatchImageInput = (
    batch_module.BatchImageInput
)


class FakeDB:
    def __init__(self):
        self.rollback_count = 0

    def rollback(self):
        self.rollback_count += 1


def make_image(
    filename: str,
    data: bytes = b"image-data",
) -> BatchImageInput:
    return BatchImageInput(
        image_bytes=data,
        original_filename=filename,
        content_type="image/jpeg",
    )


def make_user():
    return SimpleNamespace(
        id=1,
        role="USER",
    )


def test_all_images_completed(
    monkeypatch,
):
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    def fake_analyze_image(
        self,
        db,
        current_user,
        *,
        image_bytes,
        original_filename,
        content_type,
        model_id,
    ):
        return {
            "original_filename": (
                original_filename
            )
        }

    monkeypatch.setattr(
        type(batch_module.analysis_service),
        "analyze_image",
        fake_analyze_image,
    )

    result = service.analyze_images(
        db,
        user,
        images=[
            make_image("chest1.jpg"),
            make_image("chest2.jpg"),
        ],
        model_id=1,
    )

    assert result["total"] == 2
    assert result["completed"] == 2
    assert result["rejected"] == 0
    assert result["failed"] == 0

    assert (
        result["items"][0]["status"]
        == "COMPLETED"
    )

    assert (
        result["items"][1]["status"]
        == "COMPLETED"
    )

    assert db.rollback_count == 0


def test_rejected_image_does_not_abort_batch(
    monkeypatch,
):
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    def fake_analyze_image(
        self,
        db,
        current_user,
        *,
        image_bytes,
        original_filename,
        content_type,
        model_id,
    ):
        if original_filename == "cat.jpg":
            raise ValueError(
                "Image does not appear "
                "to be a chest X-ray."
            )

        return {
            "original_filename": (
                original_filename
            )
        }

    monkeypatch.setattr(
        type(batch_module.analysis_service),
        "analyze_image",
        fake_analyze_image,
    )

    result = service.analyze_images(
        db,
        user,
        images=[
            make_image("chest1.jpg"),
            make_image("cat.jpg"),
            make_image("chest2.jpg"),
        ],
        model_id=1,
    )

    assert result["total"] == 3
    assert result["completed"] == 2
    assert result["rejected"] == 1
    assert result["failed"] == 0

    assert (
        result["items"][0]["status"]
        == "COMPLETED"
    )

    assert (
        result["items"][1]["status"]
        == "REJECTED"
    )

    assert (
        result["items"][2]["status"]
        == "COMPLETED"
    )

    assert (
        result["items"][1]["analysis"]
        is None
    )

    assert (
        "chest X-ray"
        in result["items"][1]["error"]
    )

    assert db.rollback_count == 1


def test_internal_failure_does_not_abort_batch(
    monkeypatch,
):
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    def fake_analyze_image(
        self,
        db,
        current_user,
        *,
        image_bytes,
        original_filename,
        content_type,
        model_id,
    ):
        if original_filename == "broken.jpg":
            raise RuntimeError(
                "Simulated internal failure."
            )

        return {
            "original_filename": (
                original_filename
            )
        }

    monkeypatch.setattr(
        type(batch_module.analysis_service),
        "analyze_image",
        fake_analyze_image,
    )

    result = service.analyze_images(
        db,
        user,
        images=[
            make_image("chest1.jpg"),
            make_image("broken.jpg"),
            make_image("chest2.jpg"),
        ],
        model_id=1,
    )

    assert result["total"] == 3
    assert result["completed"] == 2
    assert result["rejected"] == 0
    assert result["failed"] == 1

    assert (
        result["items"][1]["status"]
        == "FAILED"
    )

    assert (
        result["items"][1]["analysis"]
        is None
    )

    assert (
        result["items"][1]["error"]
        == (
            "Image analysis failed "
            "due to an internal error."
        )
    )

    assert db.rollback_count == 1


def test_lookup_error_aborts_batch(
    monkeypatch,
):
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    def fake_analyze_image(
        self,
        db,
        current_user,
        *,
        image_bytes,
        original_filename,
        content_type,
        model_id,
    ):
        raise LookupError(
            "Patient profile not found."
        )

    monkeypatch.setattr(
        type(batch_module.analysis_service),
        "analyze_image",
        fake_analyze_image,
    )

    with pytest.raises(
        LookupError,
        match="Patient profile not found",
    ):
        service.analyze_images(
            db,
            user,
            images=[
                make_image("chest1.jpg"),
            ],
            model_id=1,
        )

    assert db.rollback_count == 1


def test_empty_batch_is_rejected():
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    with pytest.raises(
        ValueError,
        match="At least one image",
    ):
        service.analyze_images(
            db,
            user,
            images=[],
            model_id=1,
        )


def test_too_many_files_are_rejected():
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    images = [
        make_image(
            f"image_{index}.jpg"
        )
        for index in range(
            batch_module.MAX_BATCH_FILES + 1
        )
    ]

    with pytest.raises(
        ValueError,
        match="Too many files",
    ):
        service.analyze_images(
            db,
            user,
            images=images,
            model_id=1,
        )


def test_total_batch_size_is_limited(
    monkeypatch,
):
    service = BatchAnalysisService()
    db = FakeDB()
    user = make_user()

    monkeypatch.setattr(
        batch_module,
        "MAX_BATCH_TOTAL_BYTES",
        5,
    )

    images = [
        make_image(
            "image1.jpg",
            b"abc",
        ),
        make_image(
            "image2.jpg",
            b"def",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Batch size is too large",
    ):
        service.analyze_images(
            db,
            user,
            images=images,
            model_id=1,
        )