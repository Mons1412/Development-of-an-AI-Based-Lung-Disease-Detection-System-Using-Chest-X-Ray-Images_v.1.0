from uuid import uuid4

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    PatientProfileModel,
    UserModel,
)
from lung_xray_api.infrastructure.persistence.repositories.patient_profile_repository import (
    PatientProfileRepository,
)
from lung_xray_api.infrastructure.persistence.repositories.user_repository import (
    UserRepository,
)
from lung_xray_api.schemas.patient_profile import (
    PatientProfileCreate,
    PatientProfileUpdate,
)


class PatientProfileService:

    def __init__(self) -> None:
        self.repository = (
            PatientProfileRepository()
        )

        self.user_repository = (
            UserRepository()
        )

    @staticmethod
    def _normalize_phone(
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

        if (
            len(digits) < 8
            or len(digits) > 15
        ):
            raise ValueError(
                "Phone number must contain "
                "between 8 and 15 digits."
            )

        return digits

    def _generate_patient_code(
        self,
        db: Session,
    ) -> str:
        for _ in range(10):
            code = (
                "PX"
                + uuid4().hex[
                    :10
                ].upper()
            )

            existing = (
                self.repository
                .get_by_patient_code(
                    db,
                    code,
                )
            )

            if existing is None:
                return code

        raise RuntimeError(
            "Could not generate a unique "
            "patient code."
        )

    @staticmethod
    def _build_response(
        profile: PatientProfileModel,
        user: UserModel,
    ) -> dict[str, object]:
        return {
            "id":
                profile.id,

            "user_id":
                profile.user_id,

            "patient_code":
                profile.patient_code,

            "full_name":
                profile.full_name,

            "date_of_birth":
                profile.date_of_birth,

            "sex":
                profile.gender,

            "phone":
                profile.phone,

            "email":
                user.email,

            "height_cm":
                profile.height_cm,

            "weight_kg":
                profile.weight_kg,

            "created_at":
                profile.created_at,

            "updated_at":
                profile.updated_at,
        }

    def _validate_identity_fields(
        self,
        db: Session,
        current_user: UserModel,
        *,
        phone: str,
        email: str,
    ) -> None:
        phone_owner = (
            self.user_repository
            .get_by_phone(
                db,
                phone,
            )
        )

        if (
            phone_owner is not None
            and phone_owner.id
            != current_user.id
        ):
            raise ValueError(
                "Phone already exists."
            )

        email_owner = (
            self.user_repository
            .get_by_email(
                db,
                email,
            )
        )

        if (
            email_owner is not None
            and email_owner.id
            != current_user.id
        ):
            raise ValueError(
                "Email already exists."
            )

    def create_profile(
        self,
        db: Session,
        current_user: UserModel,
        request: PatientProfileCreate,
    ) -> dict[str, object]:
        existing = (
            self.repository
            .get_by_user_id(
                db,
                current_user.id,
            )
        )

        if existing is not None:
            raise ValueError(
                "Patient profile already exists."
            )

        phone = self._normalize_phone(
            request.phone
        )

        email = str(
            request.email
        ).strip().lower()

        self._validate_identity_fields(
            db,
            current_user,
            phone=phone,
            email=email,
        )

        profile = PatientProfileModel(
            user_id=current_user.id,
            patient_code=(
                self._generate_patient_code(
                    db
                )
            ),
            full_name=(
                request.full_name.strip()
            ),
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

        current_user.phone = phone
        current_user.email = email

        try:
            db.add(
                profile
            )

            db.commit()

            db.refresh(
                profile
            )

            db.refresh(
                current_user
            )

            return self._build_response(
                profile,
                current_user,
            )

        except Exception:
            db.rollback()
            raise

    def get_my_profile(
        self,
        db: Session,
        current_user: UserModel,
    ) -> dict[str, object]:
        profile = (
            self.repository
            .get_by_user_id(
                db,
                current_user.id,
            )
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found."
            )

        return self._build_response(
            profile,
            current_user,
        )

    def update_my_profile(
        self,
        db: Session,
        current_user: UserModel,
        request: PatientProfileUpdate,
    ) -> dict[str, object]:
        profile = (
            self.repository
            .get_by_user_id(
                db,
                current_user.id,
            )
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found."
            )

        changes = request.model_dump(
            exclude_unset=True
        )

        for field_name, value in changes.items():
            if value is None:
                raise ValueError(
                    field_name
                    + " cannot be null."
                )

        phone = (
            self._normalize_phone(
                changes["phone"]
            )
            if "phone" in changes
            else current_user.phone
        )

        email = (
            str(
                changes["email"]
            ).strip().lower()
            if "email" in changes
            else current_user.email
        )

        if (
            phone is None
            or email is None
        ):
            raise ValueError(
                "Phone and email are required."
            )

        self._validate_identity_fields(
            db,
            current_user,
            phone=phone,
            email=email,
        )

        if "full_name" in changes:
            profile.full_name = (
                changes[
                    "full_name"
                ].strip()
            )

        if "date_of_birth" in changes:
            profile.date_of_birth = (
                changes[
                    "date_of_birth"
                ]
            )

            profile.birth_year = (
                changes[
                    "date_of_birth"
                ].year
            )

        if "sex" in changes:
            profile.gender = (
                changes["sex"]
            )

        if "height_cm" in changes:
            profile.height_cm = (
                changes["height_cm"]
            )

        if "weight_kg" in changes:
            profile.weight_kg = (
                changes["weight_kg"]
            )

        profile.phone = phone

        current_user.phone = phone
        current_user.email = email

        try:
            db.commit()

            db.refresh(
                profile
            )

            db.refresh(
                current_user
            )

            return self._build_response(
                profile,
                current_user,
            )

        except Exception:
            db.rollback()
            raise


patient_profile_service = (
    PatientProfileService()
)
