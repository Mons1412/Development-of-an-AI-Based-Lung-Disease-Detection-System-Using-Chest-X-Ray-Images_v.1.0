import pytest

from lung_xray_api.core.exceptions import ImageValidationError
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from tests.conftest import make_image_bytes


def test_validator_accepts_real_jpeg_bytes():
    image = ImageValidator(max_upload_bytes=1024 * 1024).validate(
        make_image_bytes("JPEG"),
        filename="sample.jpg",
        content_type="image/jpeg",
    )

    assert image.detected_format == "jpeg"
    assert image.content_type == "image/jpeg"
    assert image.width == 64
    assert image.height == 64


def test_validator_accepts_png_with_octet_stream():
    image = ImageValidator(max_upload_bytes=1024 * 1024).validate(
        make_image_bytes("PNG"),
        filename="sample.png",
        content_type="application/octet-stream",
    )

    assert image.detected_format == "png"
    assert image.content_type == "application/octet-stream"


def test_validator_accepts_blank_mime_as_neutral():
    image = ImageValidator(max_upload_bytes=1024 * 1024).validate(
        make_image_bytes("JPEG"),
        filename="sample.jpeg",
        content_type="   ",
    )

    assert image.detected_format == "jpeg"
    assert image.content_type is None


def test_validator_normalizes_mime_parameters():
    image = ImageValidator(max_upload_bytes=1024 * 1024).validate(
        make_image_bytes("JPEG"),
        filename="sample.jpg",
        content_type=" IMAGE/JPEG ; charset=binary",
    )

    assert image.detected_format == "jpeg"
    assert image.content_type == "image/jpeg"


def test_validator_rejects_text_payload():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024).validate(
            b"not an image",
            filename="bad.txt",
            content_type="text/plain",
        )


def test_validator_rejects_zero_byte_payload():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024).validate(
            b"",
            filename="empty.jpg",
            content_type="image/jpeg",
        )


def test_validator_rejects_spoofed_mime_type():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024 * 1024).validate(
            make_image_bytes("JPEG"),
            filename="sample.jpg",
            content_type="text/plain",
        )


def test_validator_rejects_unsupported_image_format():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024 * 1024).validate(
            b"GIF89a",
            filename="sample.gif",
            content_type="image/gif",
        )


def test_validator_rejects_oversized_payload():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=4).validate(
            make_image_bytes("JPEG"),
            filename="sample.jpg",
            content_type="image/jpeg",
        )


def test_validator_rejects_extension_mismatch():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024 * 1024).validate(
            make_image_bytes("PNG"),
            filename="sample.jpg",
            content_type="application/octet-stream",
        )


def test_validator_rejects_specific_mime_mismatch():
    with pytest.raises(ImageValidationError):
        ImageValidator(max_upload_bytes=1024 * 1024).validate(
            make_image_bytes("PNG"),
            filename="sample.png",
            content_type="image/jpeg",
        )
