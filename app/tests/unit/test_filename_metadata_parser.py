from __future__ import annotations

from datetime import date

from lung_xray_api.application.filename_metadata_parser import (
    FILENAME_PATTERN_ID,
    FilenameMetadataParser,
)


def test_parser_matches_the_approved_filename_convention() -> None:
    result = FilenameMetadataParser().parse("BN001__NGUYEN_VAN_A__20260726.png")

    assert FILENAME_PATTERN_ID == "patient_code__patient_name__yyyymmdd_v1"
    assert result.matched is True
    assert result.patient_code == "BN001"
    assert result.patient_display_name == "NGUYEN VAN A"
    assert result.parsed_date == date(2026, 7, 26)
    assert result.validation_warnings == ()


def test_parser_preserves_unicode_vietnamese_name() -> None:
    result = FilenameMetadataParser().parse("PT-0007__TRẦN_THỊ_B__20260726.jpg")

    assert result.matched is True
    assert result.patient_code == "PT-0007"
    assert result.patient_display_name == "TRẦN THỊ B"


def test_parser_returns_no_partial_metadata_for_invalid_or_generic_names() -> None:
    parser = FilenameMetadataParser()

    for filename in (
        "image_001.png",
        "BN001__NGUYEN_VAN_A__20260230.png",
        "../BN001__NGUYEN_VAN_A__20260726.png",
        r"C:\fakepath\BN001__NGUYEN_VAN_A__20260726.png",
        "BN001___NGUYEN_VAN_A__20260726.png",
        "A" * 256,
    ):
        result = parser.parse(filename)
        assert result.matched is False
        assert result.patient_code is None
        assert result.patient_display_name is None
        assert result.parsed_date is None
        assert result.validation_warnings
