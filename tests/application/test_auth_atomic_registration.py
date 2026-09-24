from decimal import Decimal
from types import SimpleNamespace

import pytest

from lung_xray_api.application.services.auth_service import (
    AuthService,
)
from lung_xray_api.core.security import (
    verify_password,
)
from lung_xray_api.infrastructure.persistence.orm import (
    MedicalHistoryModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.schemas.auth import (
    RegisterRequest,
)


class FakeUserRepository:

    def __init__(
        self,
        *,
        phone_user=None,
        email_user=None,
    ):
        self.phone_user = phone_user
        self.email_user = email_user

    def get_by_phone(
        self,
        db,
        phone,
    ):
        del db
        del phone

        return self.phone_user

    def get_by_email(
        self,
        db,
        email,
    ):
        del db
        del email

        return self.email_user

    def get_by_username(
        self,
        db,
        username,
    ):
        del db
        del username

        return None


class FakePatientRepository:

    def get_by_patient_code(
        self,
        db,
        patient_code,
    ):
        del db
        del patient_code

        return None


class FakeSession:

    def __init__(
        self,
        *,
        fail_on_flush=None,
    ):
        self.added = []

        self.flush_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.refresh_count = 0

        self.fail_on_flush = (
            fail_on_flush
        )

        self.next_id = 1

    def add(
        self,
        model,
    ):
        self.added.append(
            model
        )

    def flush(
        self,
    ):
        self.flush_count += 1

        if (
            self.fail_on_flush
            == self.flush_count
        ):
            raise RuntimeError(
                "Injected flush failure."
            )

        for model in self.added:
            if (
                getattr(
                    model,
                    "id",
                    None,
                )
                is None
            ):
                model.id = (
                    self.next_id
                )

                self.next_id += 1

    def commit(
        self,
    ):
        self.commit_count += 1

    def rollback(
        self,
    ):
        self.rollback_count += 1

    def refresh(
        self,
        model,
    ):
        del model

        self.refresh_count += 1


def make_request():
    return RegisterRequest(
        full_name=(
            "Nguyen Van A"
        ),
        date_of_birth=(
            "15/08/2000"
        ),
        sex="MALE",
        phone=(
            "+84 901 234 567"
        ),
        email=(
            "atomic@example.com"
        ),
        height_cm=Decimal(
            "175.00"
        ),
        weight_kg=Decimal(
            "65.00"
        ),
        current_complaint_hpi=(
            "Persistent cough."
        ),
        past_medical_history=(
            "No major previous disease."
        ),
        past_medication_history=(
            "No regular medication."
        ),
        allergy_history=(
            "No known allergy."
        ),
        diet=(
            "Regular mixed diet."
        ),
        appetite=(
            "Normal appetite."
        ),
        sleep=(
            "Approximately 7 hours."
        ),
        exercise=(
            "Light exercise."
        ),
        bowel_bladder=(
            "Normal."
        ),
        habits=(
            "No smoking or alcohol."
        ),
        family_history=(
            "No relevant family history."
        ),
        password=(
            "StrongPassword123!"
        ),
        confirm_password=(
            "StrongPassword123!"
        ),
    )


def make_service(
    *,
    phone_user=None,
    email_user=None,
):
    service = AuthService()

    service.user_repository = (
        FakeUserRepository(
            phone_user=phone_user,
            email_user=email_user,
        )
    )

    service.patient_repository = (
        FakePatientRepository()
    )

    return service


def test_registration_creates_three_models_atomically():
    service = make_service()

    db = FakeSession()

    request = make_request()

    user = service.register_user(
        db,
        request,
    )

    assert isinstance(
        user,
        UserModel,
    )

    assert len(
        db.added
    ) == 3

    created_user = db.added[0]
    patient = db.added[1]
    history = db.added[2]

    assert isinstance(
        created_user,
        UserModel,
    )

    assert isinstance(
        patient,
        PatientProfileModel,
    )

    assert isinstance(
        history,
        MedicalHistoryModel,
    )

    assert (
        created_user.phone
        == "0901234567"
    )

    assert (
        created_user.username
        == "USR_0901234567"
    )

    assert verify_password(
        request.password,
        created_user.password_hash,
    )

    assert (
        patient.user_id
        == created_user.id
    )

    assert (
        patient.full_name
        == "Nguyen Van A"
    )

    assert (
        patient.birth_year
        == 2000
    )

    assert (
        str(
            patient.date_of_birth
        )
        == "2000-08-15"
    )

    assert (
        patient.gender
        == "MALE"
    )

    assert (
        patient.phone
        == "0901234567"
    )

    assert (
        history.patient_id
        == patient.id
    )

    assert (
        history.current_complaint_hpi
        == "Persistent cough."
    )

    assert (
        history.family_history
        == (
            "No relevant "
            "family history."
        )
    )

    assert (
        db.flush_count
        == 2
    )

    assert (
        db.commit_count
        == 1
    )

    assert (
        db.rollback_count
        == 0
    )


def test_duplicate_phone_is_rejected_before_writes():
    existing = SimpleNamespace(
        id=99
    )

    service = make_service(
        phone_user=existing
    )

    db = FakeSession()

    with pytest.raises(
        ValueError,
        match="Phone already exists",
    ):
        service.register_user(
            db,
            make_request(),
        )

    assert db.added == []
    assert db.commit_count == 0


def test_duplicate_email_is_rejected_before_writes():
    existing = SimpleNamespace(
        id=99
    )

    service = make_service(
        email_user=existing
    )

    db = FakeSession()

    with pytest.raises(
        ValueError,
        match="Email already exists",
    ):
        service.register_user(
            db,
            make_request(),
        )

    assert db.added == []
    assert db.commit_count == 0


def test_failure_rolls_back_without_commit():
    service = make_service()

    db = FakeSession(
        fail_on_flush=2
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Injected flush failure"
        ),
    ):
        service.register_user(
            db,
            make_request(),
        )

    assert (
        db.commit_count
        == 0
    )

    assert (
        db.rollback_count
        == 1
    )
