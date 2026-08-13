"""Bounded multipart upload reader shared by prediction endpoints."""

from __future__ import annotations

from fastapi import UploadFile

from lung_xray_api.core.exceptions import ImageValidationError

_CHUNK_SIZE = 64 * 1024


async def read_upload_bounded(upload: UploadFile, max_bytes: int) -> bytes:
    """Read at most ``max_bytes + 1`` and reject oversized payloads early."""

    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than zero")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(_CHUNK_SIZE, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise ImageValidationError("File ảnh vượt quá giới hạn dung lượng")
    return b"".join(chunks)
