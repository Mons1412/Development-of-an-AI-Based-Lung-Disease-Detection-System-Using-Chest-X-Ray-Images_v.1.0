from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.analysis_service import (
    AnalysisService,
)


def make_patient(
    *,
    patient_id: int = 10,
    user_id: int = 20,
    patient_code: str = "PXTEST001",
):
    return SimpleNamespace(
        id=patient_id,
        user_id=user_id,
        patient_code=patient_code,
    )


def make_user(
    *,
    user_id: int = 20,
):
    return SimpleNamespace(
        id=user_id,
    )


def make_analysis(
    analysis_id: int,
):
    timestamp = datetime(
        2026,
        9,
        7,
        10,
        analysis_id,
        tzinfo=timezone.utc,
    )

    return SimpleNamespace(
        id=analysis_id,
        analysis_code=f"AN{analysis_id:04d}",
        ai_model=SimpleNamespace(
            id=1,
            model_key="mobilenetv2",
            version="1.1.0",
        ),
        input_source="UPLOAD",
        original_filename=(
            f"xray_{analysis_id}.png"
        ),
        status="COMPLETED",
        prediction=None,
        created_at=timestamp,
        completed_at=timestamp,
    )


class FakePatientRepository:

    def __init__(
        self,
        *,
        own_patient=None,
        patient_by_code=None,
    ):
        self.own_patient = own_patient
        self.patient_by_code = patient_by_code
        self.last_user_id = None
        self.last_patient_code = None

    def get_by_user_id(
        self,
        db,
        user_id,
    ):
        self.last_user_id = user_id

        return self.own_patient

    def get_by_patient_code(
        self,
        db,
        patient_code,
    ):
        self.last_patient_code = patient_code

        return self.patient_by_code


class FakeAnalysisRepository:

    def __init__(
        self,
        analyses=None,
    ):
        self.analyses = list(
            analyses or []
        )

        self.patient_ids = []

    def list_by_patient_id(
        self,
        db,
        patient_id,
        *,
        limit=None,
        offset=0,
    ):
        self.patient_ids.append(
            patient_id
        )

        if limit is None:
            return list(
                self.analyses[
                    offset:
                ]
            )

        return list(
            self.analyses[
                offset:
                offset + limit
            ]
        )


def build_service(
    *,
    own_patient=None,
    patient_by_code=None,
    analyses=None,
):
    service = AnalysisService()

    service.patient_repository = (
        FakePatientRepository(
            own_patient=own_patient,
            patient_by_code=patient_by_code,
        )
    )

    service.analysis_repository = (
        FakeAnalysisRepository(
            analyses=analyses,
        )
    )

    return service


def test_user_can_list_own_history_with_pagination():
    patient = make_patient(
        patient_id=10,
        user_id=20,
        patient_code="PXTEST001",
    )

    user = make_user(
        user_id=20,
    )

    analyses = [
        make_analysis(index)
        for index in range(1, 6)
    ]

    service = build_service(
        own_patient=patient,
        analyses=analyses,
    )

    result = service.list_my_analyses(
        object(),
        user,
        patient_code=" pxtest001 ",
        limit=2,
        offset=1,
    )

    assert [
        item["id"]
        for item in result
    ] == [
        2,
        3,
    ]

    assert (
        service
        .patient_repository
        .last_user_id
        == 20
    )

    assert (
        service
        .analysis_repository
        .patient_ids
        == [10]
    )


def test_user_cannot_search_another_patient():
    patient = make_patient(
        patient_code="PXTEST001",
    )

    user = make_user()

    service = build_service(
        own_patient=patient,
        analyses=[
            make_analysis(1),
        ],
    )

    with pytest.raises(
        LookupError,
        match="Patient not found",
    ):
        service.list_my_analyses(
            object(),
            user,
            patient_code="PXOTHER999",
            limit=20,
            offset=0,
        )

    assert (
        service
        .analysis_repository
        .patient_ids
        == []
    )


def test_user_history_rejects_invalid_limit():
    patient = make_patient()
    user = make_user()

    service = build_service(
        own_patient=patient,
    )

    with pytest.raises(
        ValueError,
        match="Limit must be between",
    ):
        service.list_my_analyses(
            object(),
            user,
            limit=101,
            offset=0,
        )


def test_admin_can_search_patient_by_code():
    patient = make_patient(
        patient_id=77,
        patient_code="PXADMIN001",
    )

    analyses = [
        make_analysis(index)
        for index in range(1, 6)
    ]

    service = build_service(
        patient_by_code=patient,
        analyses=analyses,
    )

    result = (
        service
        .list_patient_analyses_for_admin(
            object(),
            patient_code=" pxadmin001 ",
            limit=2,
            offset=2,
        )
    )

    assert [
        item["id"]
        for item in result
    ] == [
        3,
        4,
    ]

    assert (
        service
        .patient_repository
        .last_patient_code
        == "PXADMIN001"
    )

    assert (
        service
        .analysis_repository
        .patient_ids
        == [77]
    )


def test_admin_unknown_patient_returns_lookup_error():
    service = build_service(
        patient_by_code=None,
    )

    with pytest.raises(
        LookupError,
        match="Patient not found",
    ):
        (
            service
            .list_patient_analyses_for_admin(
                object(),
                patient_code="PXUNKNOWN",
                limit=20,
                offset=0,
            )
        )

    assert (
        service
        .analysis_repository
        .patient_ids
        == []
    )


def test_admin_history_rejects_negative_offset():
    patient = make_patient(
        patient_code="PXADMIN001",
    )

    service = build_service(
        patient_by_code=patient,
    )

    with pytest.raises(
        ValueError,
        match="Offset must be greater",
    ):
        (
            service
            .list_patient_analyses_for_admin(
                object(),
                patient_code="PXADMIN001",
                limit=20,
                offset=-1,
            )
        )