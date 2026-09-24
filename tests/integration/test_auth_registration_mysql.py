import os
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from lung_xray_api.application.services.auth_service import (
    AuthService,
)
from lung_xray_api.infrastructure.persistence.database import (
    SessionLocal,
    engine,
)
from lung_xray_api.infrastructure.persistence.orm import (
    MedicalHistoryModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.schemas.auth import (
    RegisterRequest,
)


pytestmark = pytest.mark.skipif(
    os.getenv(
        "RUN_MYSQL_INTEGRATION"
    ) != "1",
    reason=(
        "Real MySQL registration test "
        "requires RUN_MYSQL_INTEGRATION=1."
    ),
)


def make_request(
    *,
    phone: str,
    email: str,
) -> RegisterRequest:
    return RegisterRequest(
        full_name=(
            "M15 Integration User"
        ),
        date_of_birth=(
            "15/08/2000"
        ),
        sex="MALE",
        phone=phone,
        email=email,
        height_cm=Decimal(
            "175.00"
        ),
        weight_kg=Decimal(
            "65.00"
        ),
        current_complaint_hpi=(
            "Integration test complaint."
        ),
        past_medical_history=(
            "Integration test "
            "medical history."
        ),
        past_medication_history=(
            "Integration test "
            "medication history."
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


def test_registration_persists_all_three_models_and_rolls_back():
    assert (
        engine.dialect.name
        == "mysql"
    )

    suffix = (
        uuid4().hex[:8]
    )

    phone = (
        "09"
        + str(
            int(
                suffix,
                16,
            )
        )[-8:].zfill(8)
    )

    email = (
        "m15.integration."
        + suffix
        + "@example.com"
    )

    request = make_request(
        phone=phone,
        email=email,
    )

    service = AuthService()

    created_user_id = None
    created_patient_id = None
    created_history_id = None

    normalized_phone = (
        service.normalize_phone(
            phone
        )
    )

    with engine.connect() as connection:
        outer_transaction = (
            connection.begin()
        )

        db = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode=(
                "create_savepoint"
            ),
        )

        try:
            user = service.register_user(
                db,
                request,
            )

            created_user_id = user.id

            stored_user = db.scalar(
                select(
                    UserModel
                ).where(
                    UserModel.id
                    == user.id
                )
            )

            assert stored_user is not None

            assert (
                stored_user.phone
                == normalized_phone
            )

            assert (
                stored_user.email
                == email
            )

            assert (
                stored_user.role
                == "USER"
            )

            assert (
                stored_user.username
                == (
                    "USR_"
                    + normalized_phone
                )
            )

            patient = db.scalar(
                select(
                    PatientProfileModel
                ).where(
                    PatientProfileModel.user_id
                    == user.id
                )
            )

            assert patient is not None

            created_patient_id = (
                patient.id
            )

            assert (
                patient.full_name
                == "M15 Integration User"
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
                == normalized_phone
            )

            assert (
                patient.height_cm
                == Decimal(
                    "175.00"
                )
            )

            assert (
                patient.weight_kg
                == Decimal(
                    "65.00"
                )
            )

            history = db.scalar(
                select(
                    MedicalHistoryModel
                ).where(
                    MedicalHistoryModel.patient_id
                    == patient.id
                )
            )

            assert history is not None

            created_history_id = (
                history.id
            )

            assert (
                history.current_complaint_hpi
                == (
                    "Integration test "
                    "complaint."
                )
            )

            assert (
                history.past_medical_history
                == (
                    "Integration test "
                    "medical history."
                )
            )

            assert (
                history.past_medication_history
                == (
                    "Integration test "
                    "medication history."
                )
            )

            assert (
                history.allergy_history
                == "No known allergy."
            )

            assert (
                history.diet
                == "Regular mixed diet."
            )

            assert (
                history.appetite
                == "Normal appetite."
            )

            assert (
                history.sleep
                == (
                    "Approximately 7 hours."
                )
            )

            assert (
                history.exercise
                == "Light exercise."
            )

            assert (
                history.bowel_bladder
                == "Normal."
            )

            assert (
                history.habits
                == (
                    "No smoking or alcohol."
                )
            )

            assert (
                history.family_history
                == (
                    "No relevant "
                    "family history."
                )
            )

        finally:
            db.close()

            if (
                outer_transaction
                .is_active
            ):
                outer_transaction.rollback()

    assert (
        created_user_id
        is not None
    )

    assert (
        created_patient_id
        is not None
    )

    assert (
        created_history_id
        is not None
    )

    verification_db = (
        SessionLocal()
    )

    try:
        remaining_user = (
            verification_db.scalar(
                select(
                    UserModel
                ).where(
                    UserModel.id
                    == created_user_id
                )
            )
        )

        remaining_patient = (
            verification_db.scalar(
                select(
                    PatientProfileModel
                ).where(
                    PatientProfileModel.id
                    == created_patient_id
                )
            )
        )

        remaining_history = (
            verification_db.scalar(
                select(
                    MedicalHistoryModel
                ).where(
                    MedicalHistoryModel.id
                    == created_history_id
                )
            )
        )

        assert remaining_user is None
        assert remaining_patient is None
        assert remaining_history is None

    finally:
        verification_db.close()
