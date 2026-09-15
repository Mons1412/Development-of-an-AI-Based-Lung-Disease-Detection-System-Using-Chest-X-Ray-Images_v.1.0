from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.report_service import (
    ReportService,
)


class StubReportRepository:

    def __init__(
        self,
        report,
    ):
        self.report = report

    def get_by_id(
        self,
        db,
        report_id,
    ):
        return self.report


def make_report(
    *,
    owner_user_id: int = 10,
):
    patient = SimpleNamespace(
        user_id=owner_user_id,
    )

    analysis = SimpleNamespace(
        patient=patient,
    )

    return SimpleNamespace(
        id=51,
        analysis=analysis,
    )


def make_service(
    report,
):
    service = object.__new__(
        ReportService
    )

    service.report_repository = (
        StubReportRepository(
            report
        )
    )

    return service


def test_owner_user_can_get_report():
    report = make_report(
        owner_user_id=10
    )

    service = make_service(
        report
    )

    user = SimpleNamespace(
        id=10,
        role="USER",
    )

    result = service.get_report(
        object(),
        user,
        report_id=51,
    )

    assert result is report


def test_other_user_receives_not_found():
    report = make_report(
        owner_user_id=10
    )

    service = make_service(
        report
    )

    other_user = SimpleNamespace(
        id=11,
        role="USER",
    )

    with pytest.raises(
        LookupError,
        match="Report not found",
    ):
        service.get_report(
            object(),
            other_user,
            report_id=51,
        )


def test_admin_can_get_any_report():
    report = make_report(
        owner_user_id=10
    )

    service = make_service(
        report
    )

    admin = SimpleNamespace(
        id=999,
        role="ADMIN",
    )

    result = service.get_report(
        object(),
        admin,
        report_id=51,
    )

    assert result is report


def test_generate_report_rejects_non_completed_analysis():
    service = object.__new__(
        ReportService
    )

    analysis = SimpleNamespace(
        status="FAILED",
    )

    patient = SimpleNamespace(
        id=10,
    )

    user = SimpleNamespace(
        id=10,
        role="USER",
    )

    def fake_load_analysis_for_user(
        db,
        current_user,
        *,
        analysis_id,
    ):
        assert analysis_id == 272

        return (
            analysis,
            patient,
        )

    service._load_analysis_for_user = (
        fake_load_analysis_for_user
    )

    with pytest.raises(
        ValueError,
        match=(
            "Only completed analyses "
            "can be exported"
        ),
    ):
        service.generate_report(
            object(),
            user,
            analysis_id=272,
            language="vi",
        )


def test_report_language_contract():
    service = object.__new__(
        ReportService
    )

    assert (
        service._normalize_language(
            "VI"
        )
        == "vi"
    )

    assert (
        service._normalize_language(
            " en "
        )
        == "en"
    )

    with pytest.raises(
        ValueError,
        match="vi.*en",
    ):
        service._normalize_language(
            "fr"
        )
