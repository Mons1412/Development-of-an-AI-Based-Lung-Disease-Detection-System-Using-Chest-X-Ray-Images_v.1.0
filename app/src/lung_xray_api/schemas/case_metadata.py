"""Strict, server-validated patient/case metadata contracts."""

from __future__ import annotations

from datetime import date
import re
from typing import Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PatientNameSource = Literal["filename", "manual", "anonymous"]
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")
_HTML_CHARACTERS = frozenset({"<", ">", "&"})


def normalize_patient_code(value: object) -> str | None:
    """Normalize a bounded identifier without accepting paths or markup."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("patient_code must be text")
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        return None
    if not 2 <= len(normalized) <= 32:
        raise ValueError("patient_code must contain 2 to 32 characters")
    if (
        not normalized[0].isalnum()
        or any(not (character.isalnum() or character == "-") for character in normalized)
        or "--" in normalized
        or any(character in _HTML_CHARACTERS for character in normalized)
    ):
        raise ValueError("patient_code contains unsupported characters")
    return normalized


def normalize_patient_display_name(value: object) -> str | None:
    """Normalize a real display name while refusing markup and path-like text."""

    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("patient_display_name must be text")
    normalized = unicodedata.normalize("NFC", value)
    if _CONTROL_CHARACTERS.search(normalized):
        raise ValueError("patient_display_name contains control characters")
    normalized = " ".join(normalized.strip().split())
    if not normalized:
        return None
    if not 2 <= len(normalized) <= 80:
        raise ValueError("patient_display_name must contain 2 to 80 characters")
    if any(character in _HTML_CHARACTERS for character in normalized):
        raise ValueError("patient_display_name must not contain HTML characters")
    if any(character in {"/", "\\", "_"} for character in normalized):
        raise ValueError("patient_display_name contains unsupported separators")
    if any(
        not (character.isalpha() or unicodedata.category(character).startswith("M") or character in {" ", "-", "'"})
        for character in normalized
    ):
        raise ValueError("patient_display_name contains unsupported characters")
    if normalized.startswith(("-", "'")) or normalized.endswith(("-", "'")):
        raise ValueError("patient_display_name has an invalid boundary")
    return normalized


def parse_multipart_boolean(value: object) -> bool:
    """Accept only canonical form boolean values, never truthy arbitrary strings."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    raise ValueError("boolean fields must be true or false")


class CaseMetadataInput(BaseModel):
    """Metadata required before a new persisted analysis may start."""

    model_config = ConfigDict(extra="forbid")

    patient_code: str | None = Field(default=None, max_length=32)
    patient_display_name: str | None = Field(default=None, max_length=80)
    patient_name_source: PatientNameSource
    patient_info_confirmed: bool
    is_anonymous_sample: bool

    @field_validator("patient_code", mode="before")
    @classmethod
    def validate_patient_code(cls, value: object) -> str | None:
        return normalize_patient_code(value)

    @field_validator("patient_display_name", mode="before")
    @classmethod
    def validate_patient_display_name(cls, value: object) -> str | None:
        return normalize_patient_display_name(value)

    @field_validator("patient_info_confirmed", "is_anonymous_sample", mode="before")
    @classmethod
    def validate_boolean_fields(cls, value: object) -> bool:
        return parse_multipart_boolean(value)

    @model_validator(mode="after")
    def validate_case_mode(self) -> "CaseMetadataInput":
        if self.patient_info_confirmed is not True:
            raise ValueError("patient information must be confirmed before analysis")
        if self.is_anonymous_sample is True:
            if (
                self.patient_code is not None
                or self.patient_display_name is not None
                or self.patient_name_source != "anonymous"
            ):
                raise ValueError("anonymous samples cannot include patient identifiers")
            return self
        if self.is_anonymous_sample is not False:
            raise ValueError("is_anonymous_sample must be provided")
        if (
            self.patient_display_name is None
            or self.patient_name_source not in {"filename", "manual"}
        ):
            raise ValueError("identified cases require confirmed name and source")
        return self


class FilenameParseRequest(BaseModel):
    """Filename-only parse request. It never persists a case or starts inference."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)


class FilenameParseResponse(BaseModel):
    """All-or-nothing result of the approved filename convention parser."""

    matched: bool
    patient_code: str | None = None
    patient_display_name: str | None = None
    parsed_date: date | None = None
    source: Literal["filename"] = "filename"
    validation_warnings: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True


class CaseMetadataResponse(BaseModel):
    patient_code: str | None
    patient_display_name: str | None
    patient_name_source: PatientNameSource
    patient_info_confirmed: bool
    is_anonymous_sample: bool
