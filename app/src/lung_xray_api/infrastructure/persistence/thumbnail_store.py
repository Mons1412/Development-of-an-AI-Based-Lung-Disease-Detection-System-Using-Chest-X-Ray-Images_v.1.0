"""Atomic derivative-thumbnail storage in one controlled local directory."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import tempfile
from uuid import UUID

from PIL import Image, ImageOps, features

from lung_xray_api.core.exceptions import PersistenceError, ThumbnailCleanupError
from lung_xray_api.infrastructure.ml.image_validator import ValidatedImage

_ALLOWED_SUFFIXES = frozenset({".webp", ".jpg"})
_FORBIDDEN_PATH_TOKENS = ("/", "\\", ":", "..")


class ThumbnailStore:
    """Persist re-encoded previews only; original uploads never reach this store."""

    def __init__(self, thumbnail_directory: Path, max_dimension: int) -> None:
        if max_dimension <= 0:
            raise ValueError("thumbnail_max_dimension must be greater than zero")
        self.thumbnail_directory = thumbnail_directory.resolve()
        self.max_dimension = max_dimension

    def ensure_directory(self) -> None:
        try:
            self.thumbnail_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise PersistenceError("Could not create analysis thumbnail directory") from error

    def write_thumbnail(self, analysis_id: str, image: ValidatedImage) -> str:
        file_stem = self._validated_uuid_stem(analysis_id)
        self.ensure_directory()
        image_format, suffix = self._preferred_format()
        relative_path = f"{file_stem}{suffix}"
        destination = self._resolve_relative_path(relative_path)
        if destination.exists():
            raise PersistenceError("Thumbnail already exists for this analysis")

        temporary_path: Path | None = None
        try:
            rendered = self._render_thumbnail(image, image_format)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.thumbnail_directory,
                prefix=f".{file_stem}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(rendered)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, destination)
            return relative_path
        except (OSError, ValueError) as error:
            if temporary_path is not None:
                self._unlink_if_exists(temporary_path)
            raise PersistenceError("Could not write analysis thumbnail") from error

    def delete_thumbnail(self, relative_path: str | None) -> None:
        if relative_path is None:
            return
        path = self._resolve_relative_path(relative_path)
        try:
            path.unlink(missing_ok=True)
        except OSError as error:
            raise ThumbnailCleanupError("Could not remove analysis thumbnail") from error

    def read_thumbnail(self, relative_path: str | None) -> tuple[bytes, str]:
        if relative_path is None:
            raise PersistenceError("Analysis thumbnail is unavailable")
        path = self._resolve_relative_path(relative_path)
        if not path.is_file():
            raise PersistenceError("Analysis thumbnail is unavailable")
        try:
            content = path.read_bytes()
        except OSError as error:
            raise PersistenceError("Could not read analysis thumbnail") from error
        media_type = "image/webp" if path.suffix.lower() == ".webp" else "image/jpeg"
        return content, media_type

    def _render_thumbnail(self, validated_image: ValidatedImage, image_format: str) -> bytes:
        # Re-encoding removes embedded EXIF and bounds local sensitive data.
        with Image.open(BytesIO(validated_image.content)) as source:
            oriented = ImageOps.exif_transpose(source)
            thumbnail = oriented.convert("RGB")
            thumbnail.thumbnail(
                (self.max_dimension, self.max_dimension),
                Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            if image_format == "WEBP":
                thumbnail.save(output, format="WEBP", quality=82, method=6)
            else:
                thumbnail.save(
                    output,
                    format="JPEG",
                    quality=85,
                    optimize=True,
                    progressive=True,
                )
            return output.getvalue()

    def _resolve_relative_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path:
            raise PersistenceError("Thumbnail path must be a non-empty file name")
        if any(token in relative_path for token in _FORBIDDEN_PATH_TOKENS):
            raise PersistenceError("Thumbnail path contains a forbidden path token")
        candidate = Path(relative_path)
        if candidate.is_absolute() or len(candidate.parts) != 1:
            raise PersistenceError(
                "Thumbnail path must be relative to the thumbnail directory"
            )
        if candidate.suffix.lower() not in _ALLOWED_SUFFIXES:
            raise PersistenceError("Thumbnail path has an unsupported extension")
        if candidate.name != relative_path or candidate.name.startswith("."):
            raise PersistenceError("Thumbnail path is invalid")
        resolved = (self.thumbnail_directory / candidate).resolve()
        try:
            resolved.relative_to(self.thumbnail_directory)
        except ValueError as error:
            raise PersistenceError("Thumbnail path escapes the configured directory") from error
        return resolved

    @staticmethod
    def _validated_uuid_stem(analysis_id: str) -> str:
        try:
            parsed = UUID(analysis_id)
        except (ValueError, AttributeError) as error:
            raise PersistenceError("Analysis ID must be a UUID") from error
        if str(parsed) != analysis_id:
            raise PersistenceError("Analysis ID must use canonical UUID format")
        return analysis_id

    @staticmethod
    def _preferred_format() -> tuple[str, str]:
        return ("WEBP", ".webp") if features.check("webp") else ("JPEG", ".jpg")

    @staticmethod
    def _unlink_if_exists(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
