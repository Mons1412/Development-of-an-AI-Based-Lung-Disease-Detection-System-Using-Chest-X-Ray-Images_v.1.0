from sqlalchemy import (
    select,
)
from sqlalchemy.orm import (
    Session,
)

from lung_xray_api.infrastructure.persistence.orm.medical_history_model import (
    MedicalHistoryModel,
)
from lung_xray_api.infrastructure.persistence.orm.patient_profile_model import (
    PatientProfileModel,
)
from lung_xray_api.infrastructure.persistence.orm.user_model import (
    UserModel,
)
from lung_xray_api.schemas.medical_history_intake import (
    MedicalHistoryIntakeCreate,
)


class MedicalHistoryIntakeService:

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

    def list_page(
        self,
        db: Session,
        current_user: UserModel,
        *,
        limit: int,
        offset: int,
    ) -> dict:
        profile = self._get_profile(
            db,
            current_user,
        )


        statement = (
            select(
                MedicalHistoryModel
            )
            .where(
                MedicalHistoryModel.patient_id
                == profile.id
            )
            .order_by(
                MedicalHistoryModel.recorded_at.desc(),
                MedicalHistoryModel.id.desc(),
            )
            .offset(
                offset
            )
            .limit(
                limit + 1
            )
        )


        rows = list(
            db.scalars(
                statement
            ).all()
        )


        has_more = (
            len(
                rows
            )
            > limit
        )


        items = rows[
            :limit
        ]


        return {
            "items":
                items,

            "limit":
                limit,

            "offset":
                offset,

            "has_more":
                has_more,
        }

    def create_history(
        self,
        db: Session,
        current_user: UserModel,
        request: MedicalHistoryIntakeCreate,
    ) -> MedicalHistoryModel:
        profile = self._get_profile(
            db,
            current_user,
        )


        payload = (
            request.model_dump()
        )


        for (
            key,
            value
        ) in payload.items():
            if (
                isinstance(
                    value,
                    str,
                )
            ):
                cleaned = (
                    value.strip()
                )

                payload[
                    key
                ] = (
                    cleaned
                    if cleaned
                    else None
                )


        history = (
            MedicalHistoryModel(
                patient_id=
                    profile.id,

                **payload,
            )
        )


        try:
            db.add(
                history
            )

            db.commit()

            db.refresh(
                history
            )

            return history

        except Exception:
            db.rollback()
            raise


medical_history_intake_service = (
    MedicalHistoryIntakeService()
)
