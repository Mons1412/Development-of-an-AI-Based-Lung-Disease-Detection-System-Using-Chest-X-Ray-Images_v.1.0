from uuid import uuid4

from sqlalchemy.orm import Session

from lung_xray_api.core.security import (
    hash_password,
    verify_password,
)
from lung_xray_api.infrastructure.persistence.orm import (
    MedicalHistoryModel,
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from lung_xray_api.schemas.auth import RegisterRequest


class AuthService:

    def __init__(self) -> None:
        self.user_repository = (
            UserRepository()
        )

        self.patient_repository = (
            PatientProfileRepository()
        )

    @staticmethod
    def normalize_phone(
        raw_phone: str,
    ) -> str:
        raw = raw_phone.strip()

        digits = "".join(
            character
            for character in raw
            if character.isdigit()
        )

        if (
            raw.startswith("+84")
            and digits.startswith("84")
        ):
            digits = (
                "0"
                + digits[2:]
            )

        elif (
            digits.startswith("84")
            and len(digits) == 11
        ):
            digits = (
                "0"
                + digits[2:]
            )

        return digits

    @staticmethod
    def _validate_phone(
        phone: str,
    ) -> None:
        if (
            len(phone) < 8
            or len(phone) > 15
        ):
            raise ValueError(
                "Phone number must contain "
                "between 8 and 15 digits."
            )

        if not phone.isdigit():
            raise ValueError(
                "Phone number is invalid."
            )

    def _generate_internal_username(
        self,
        db: Session,
        phone: str,
    ) -> str:
        base_username = (
            "USR_"
            + phone
        )

        existing = (
            self.user_repository
            .get_by_username(
                db,
                base_username,
            )
        )

        if existing is None:
            return base_username

        for _ in range(10):
            candidate = (
                base_username
                + "_"
                + uuid4().hex[
                    :6
                ].upper()
            )

            existing = (
                self.user_repository
                .get_by_username(
                    db,
                    candidate,
                )
            )

            if existing is None:
                return candidate

        raise RuntimeError(
            "Could not generate a unique "
            "internal username."
        )

    def _generate_patient_code(
        self,
        db: Session,
    ) -> str:
        for _ in range(10):
            patient_code = (
                "PX"
                + uuid4().hex[
                    :10
                ].upper()
            )

            existing = (
                self.patient_repository
                .get_by_patient_code(
                    db,
                    patient_code,
                )
            )

            if existing is None:
                return patient_code

        raise RuntimeError(
            "Could not generate a unique "
            "patient code."
        )

    def register_user(
        self,
        db: Session,
        request: RegisterRequest,
    ) -> UserModel:
        phone = self.normalize_phone(
            request.phone
        )

        self._validate_phone(
            phone
        )

        email = str(
            request.email
        ).strip().lower()

        existing_phone = (
            self.user_repository
            .get_by_phone(
                db,
                phone,
            )
        )

        if existing_phone is not None:
            raise ValueError(
                "Phone already exists."
            )

        existing_email = (
            self.user_repository
            .get_by_email(
                db,
                email,
            )
        )

        if existing_email is not None:
            raise ValueError(
                "Email already exists."
            )

        username = (
            self._generate_internal_username(
                db,
                phone,
            )
        )

        patient_code = (
            self._generate_patient_code(
                db
            )
        )

        password_hash = hash_password(
            request.password
        )

        try:
            user = UserModel(
                username=username,
                phone=phone,
                email=email,
                password_hash=password_hash,
                role="USER",
                is_active=True,
            )

            db.add(
                user
            )

            db.flush()

            patient = PatientProfileModel(
                user_id=user.id,
                patient_code=patient_code,
                full_name=request.full_name,
                birth_year=(
                    request.date_of_birth.year
                ),
                date_of_birth=(
                    request.date_of_birth
                ),
                gender=request.sex,
                phone=phone,
                address=None,
                height_cm=request.height_cm,
                weight_kg=request.weight_kg,
            )

            db.add(
                patient
            )

            db.flush()

            medical_history = (
                MedicalHistoryModel(
                    patient_id=patient.id,
                    current_complaint_hpi=(
                        request
                        .current_complaint_hpi
                    ),
                    past_medical_history=(
                        request
                        .past_medical_history
                    ),
                    past_medication_history=(
                        request
                        .past_medication_history
                    ),
                    allergy_history=(
                        request
                        .allergy_history
                    ),
                    diet=request.diet,
                    appetite=request.appetite,
                    sleep=request.sleep,
                    exercise=request.exercise,
                    bowel_bladder=(
                        request
                        .bowel_bladder
                    ),
                    habits=request.habits,
                    family_history=(
                        request
                        .family_history
                    ),
                    diseases=request.diseases,
                    medications=[
                        request
                        .past_medication_history
                    ],
                    allergies=None,
                    smoking_status=(
                        request.smoking_status
                    ),
                    alcohol_status=(
                        request.alcohol_status
                    ),
                    occupational_exposure=(
                        request
                        .occupational_exposure
                    ),
                    notes=(
                        request
                        .current_complaint_hpi
                    ),
                )
            )

            db.add(
                medical_history
            )

            db.commit()

            db.refresh(
                user
            )

            return user

        except Exception:
            db.rollback()
            raise

    def authenticate_user(
        self,
        db: Session,
        identifier: str,
        password: str,
    ) -> UserModel | None:
        normalized_identifier = (
            identifier.strip()
        )

        normalized_phone = (
            self.normalize_phone(
                normalized_identifier
            )
        )

        user = None

        if normalized_phone:
            user = (
                self.user_repository
                .get_by_phone(
                    db,
                    normalized_phone,
                )
            )

        if user is None:
            legacy_user = (
                self.user_repository
                .get_by_username(
                    db,
                    normalized_identifier,
                )
            )

            if (
                legacy_user is not None
                and legacy_user.role
                == "ADMIN"
            ):
                user = legacy_user

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user


auth_service = AuthService()
