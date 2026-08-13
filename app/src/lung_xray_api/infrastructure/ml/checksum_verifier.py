"""Xác minh checksum cho artifact model.

Kỹ thuật chính là streaming SHA-256: đọc file theo chunk để tính hash mà không
đưa toàn bộ `.keras` vào RAM. Time complexity là O(n) theo kích thước file,
extra memory là O(1) ngoài buffer đọc file.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from lung_xray_api.core.exceptions import ArtifactError


@dataclass(frozen=True)
class ChecksumResult:
    file_name: str
    expected: str
    actual: str

    @property
    def ok(self) -> bool:
        return self.expected.lower() == self.actual.lower()


def calculate_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    if not path.is_file():
        raise ArtifactError(f"Artifact không tồn tại: {path}")

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_checksums(checksums_path: Path) -> dict[str, str]:
    try:
        payload = json.loads(checksums_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ArtifactError(f"Không đọc được checksums.json: {checksums_path}") from error
    except json.JSONDecodeError as error:
        raise ArtifactError("checksums.json không phải JSON hợp lệ") from error

    if not isinstance(payload, dict) or not payload:
        raise ArtifactError("checksums.json phải là object không rỗng")
    return {str(key): str(value) for key, value in payload.items()}


def verify_checksums(artifact_dir: Path) -> list[ChecksumResult]:
    checksums = load_checksums(artifact_dir / "checksums.json")
    results: list[ChecksumResult] = []
    for file_name, expected in checksums.items():
        actual = calculate_sha256(artifact_dir / file_name)
        result = ChecksumResult(file_name=file_name, expected=expected, actual=actual)
        if not result.ok:
            raise ArtifactError(f"Checksum mismatch: {file_name}")
        results.append(result)
    return results


def verify_artifact_checksums(artifact_dir: Path) -> list[ChecksumResult]:
    """Compatibility alias cho verification gate."""

    return verify_checksums(artifact_dir)
