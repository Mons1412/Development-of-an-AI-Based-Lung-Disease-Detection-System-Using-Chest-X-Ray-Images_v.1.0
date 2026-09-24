from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from lung_xray_api.core.paths import (
    PROJECT_ROOT,
    resolve_project_path,
)


UPLOAD_ROOT = resolve_project_path(
    "var/uploads/analyses"
)


class ImageStorage:

    def save(
        self,
        image_bytes: bytes,
        extension: str,
    ) -> str:

        now = datetime.now(
            timezone.utc
        )

        directory = (
            UPLOAD_ROOT
            / now.strftime("%Y")
            / now.strftime("%m")
            / now.strftime("%d")
        )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            f"{uuid4().hex}.{extension}"
        )

        absolute_path = (
            directory / filename
        )

        absolute_path.write_bytes(
            image_bytes
        )

        relative_path = (
            absolute_path
            .relative_to(PROJECT_ROOT)
            .as_posix()
        )

        return relative_path

    def delete(
        self,
        relative_path: str,
    ) -> None:

        path = resolve_project_path(
            relative_path
        )

        if path.is_file():
            path.unlink()


image_storage = ImageStorage()