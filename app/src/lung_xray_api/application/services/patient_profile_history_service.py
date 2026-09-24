from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    select,
)
from sqlalchemy.orm import (
    Session,
)

from lung_xray_api.infrastructure.persistence.orm.patient_profile_history_model import (
    PatientProfileHistoryModel,
)
from lung_xray_api.infrastructure.persistence.orm.patient_profile_model import (
    PatientProfileModel,
)
from lung_xray_api.infrastructure.persistence.orm.user_model import (
    UserModel,
)
from lung_xray_api.schemas.patient_profile_history import (
    PatientProfileMeasurementUpdate,
)


class PatientProfileHistoryService:

    @staticmethod
    def _now() -> datetime:
        return (
            datetime.now(
                timezone.utc
            )
            .replace(
                tzinfo=None
            )
        )

    @staticmethod
    def _get_profile(
        db: Session,
        current_user: UserModel,
    ) -> PatientProfileModel:
        statement = (
            select(
                PatientProfileModel
            )
            .where(
                PatientProfileModel.user_id
                == current_user.id
            )
        )

        profile = db.scalar(
            statement
        )

        if profile is None:
            raise LookupError(
                "Patient profile not found."
            )

        return profile

    def update_measurements(
        self,
        db: Session,
        current_user: UserModel,
        request: PatientProfileMeasurementUpdate,
    ) -> dict:
        profile = self._get_profile(
            db,
            current_user,
        )

        changed = (
            profile.height_cm
            != request.height_cm
            or profile.weight_kg
            != request.weight_kg
        )

        if not changed:
            return {
                "changed":
                    False,

                "height_cm":
                    profile.height_cm,

                "weight_kg":
                    profile.weight_kg,

                "recorded_at":
                    None,
            }


        recorded_at = self._now()


        try:
            profile.height_cm = (
                request.height_cm
            )

            profile.weight_kg = (
                request.weight_kg
            )


            if hasattr(
                profile,
                "updated_at",
            ):
                profile.updated_at = (
                    recorded_at
                )


            history = (
                PatientProfileHistoryModel(
                    patient_id=
                        profile.id,

                    height_cm=
                        request.height_cm,

                    weight_kg=
                        request.weight_kg,

                    recorded_at=
                        recorded_at,
                )
            )


            db.add(
                history
            )

            db.commit()

            db.refresh(
                profile
            )

            db.refresh(
                history
            )


            return {
                "changed":
                    True,

                "height_cm":
                    history.height_cm,

                "weight_kg":
                    history.weight_kg,

                "recorded_at":
                    history.recorded_at,
            }

        except Exception:
            db.rollback()
            raise

    def list_history(
        self,
        db: Session,
        current_user: UserModel,
    ) -> list[
        PatientProfileHistoryModel
    ]:
        profile = self._get_profile(
            db,
            current_user,
        )


        statement = (
            select(
                PatientProfileHistoryModel
            )
            .where(
                PatientProfileHistoryModel.patient_id
                == profile.id
            )
            .order_by(
                PatientProfileHistoryModel.recorded_at.desc(),
                PatientProfileHistoryModel.id.desc(),
            )
        )


        return list(
            db.scalars(
                statement
            ).all()
        )


patient_profile_history_service = (
    PatientProfileHistoryService()
)
