from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_BYTES = 10 * 1024 * 1024
MIN_IMAGE_DIMENSION = 64
MAX_IMAGE_PIXELS = 25_000_000

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
}

FORMAT_EXTENSIONS = {
    "JPEG": "jpg",
    "PNG": "png",
}


@dataclass(frozen=True)
class ValidatedImage:
    image_format: str
    extension: str
    width: int
    height: int


class ImageValidator:

    def validate(
        self,
        image_bytes: bytes,
        content_type: str | None,
    ) -> ValidatedImage:

        if not image_bytes:
            raise ValueError(
                "Image data is empty."
            )

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise ValueError(
                "Image is too large."
            )

        if (
            content_type
            and content_type.lower()
            not in ALLOWED_CONTENT_TYPES
        ):
            raise ValueError(
                "Only JPEG and PNG images are supported."
            )

        try:
            with Image.open(
                BytesIO(image_bytes)
            ) as image:

                image_format = (
                    image.format or ""
                ).upper()

                width, height = image.size

                image.verify()

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Invalid or corrupted image."
            ) from exc

        if image_format not in FORMAT_EXTENSIONS:
            raise ValueError(
                "Unsupported image format."
            )

        if (
            width < MIN_IMAGE_DIMENSION
            or height < MIN_IMAGE_DIMENSION
        ):
            raise ValueError(
                "Image dimensions are too small."
            )

        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(
                "Image dimensions are too large."
            )

        return ValidatedImage(
            image_format=image_format,
            extension=FORMAT_EXTENSIONS[
                image_format
            ],
            width=width,
            height=height,
        )


image_validator = ImageValidator()