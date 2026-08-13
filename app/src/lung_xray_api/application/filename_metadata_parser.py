"""Approved all-or-nothing parser for patient metadata in a filename."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
import unicodedata

from lung_xray_api.schemas.case_metadata import (
    normalize_patient_code,
    normalize_patient_display_name,
)

FILENAME_PATTERN_ID = "patient_code__patient_name__yyyymmdd_v1"
_FILENAME_PATTERN = re.compile(
    r"^(?P<patient_code>[A-Za-z0-9][A-Za-z0-9-]{1,31})"
    r"__(?P<patient_name>[^_]+(?:_[^_]+)*)"
    r"__(?P<parsed_date>\d{8})\.(?P<extension>jpg|jpeg|png)$",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class FilenameParseResult:
    matched: bool
    patient_code: str | None = None
    patient_display_name: str | None = None
    parsed_date: date | None = None
    validation_warnings: tuple[str, ...] = ()


class FilenameMetadataParser:
    """Parse only the explicitly approved basename convention.

    Contract: ``<PATIENT_CODE>__<PATIENT_NAME>__<YYYYMMDD>.<jpg|jpeg|png>``.
    A result with ``matched=False`` never carries partly inferred metadata.
    """

    def parse(self, filename: str) -> FilenameParseResult:
        normalized = unicodedata.normalize("NFC", filename)
        if len(normalized) > 255:
            return self._unmatched("filename_is_too_long")
        if not normalized or normalized != normalized.strip():
            return self._unmatched("filename_has_invalid_whitespace")
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            return self._unmatched("filename_has_unsupported_characters")
        if any(character in normalized for character in ("/", "\\", ":")):
            return self._unmatched("filename_has_suspicious_path_component")
        if normalized in {".", ".."} or ".." in normalized:
            return self._unmatched("filename_has_suspicious_path_component")

        match = _FILENAME_PATTERN.fullmatch(normalized)
        if match is None:
            return self._unmatched("filename_does_not_match_approved_convention")

        try:
            patient_code = normalize_patient_code(match.group("patient_code"))
            patient_name = normalize_patient_display_name(
                match.group("patient_name").replace("_", " ")
            )
            parsed_date = date(
                int(match.group("parsed_date")[0:4]),
                int(match.group("parsed_date")[4:6]),
                int(match.group("parsed_date")[6:8]),
            )
        except ValueError:
            return self._unmatched("filename_contains_invalid_patient_metadata_or_date")

        if patient_code is None or patient_name is None:
            return self._unmatched("filename_contains_invalid_patient_metadata_or_date")
        return FilenameParseResult(
            matched=True,
            patient_code=patient_code,
            patient_display_name=patient_name,
            parsed_date=parsed_date,
        )

    @staticmethod
    def _unmatched(warning: str) -> FilenameParseResult:
        return FilenameParseResult(matched=False, validation_warnings=(warning,))
