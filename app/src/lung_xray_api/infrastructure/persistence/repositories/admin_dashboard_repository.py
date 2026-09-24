from sqlalchemy import func, select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    AIModel,
    AnalysisModel,
    MedicalAdviceModel,
    PatientProfileModel,
    PredictionModel,
    ReportModel,
    UserModel,
)


class AdminDashboardRepository:

    def get_overview(
        self,
        db: Session,
    ) -> dict[str, int]:

        total_users = db.scalar(
            select(
                func.count(UserModel.id)
            )
        )

        active_users = db.scalar(
            select(
                func.count(UserModel.id)
            ).where(
                UserModel.is_active.is_(True)
            )
        )

        total_patients = db.scalar(
            select(
                func.count(
                    PatientProfileModel.id
                )
            )
        )

        total_analyses = db.scalar(
            select(
                func.count(
                    AnalysisModel.id
                )
            )
        )

        completed_analyses = db.scalar(
            select(
                func.count(
                    AnalysisModel.id
                )
            ).where(
                AnalysisModel.status
                == "COMPLETED"
            )
        )

        failed_analyses = db.scalar(
            select(
                func.count(
                    AnalysisModel.id
                )
            ).where(
                AnalysisModel.status
                == "FAILED"
            )
        )

        total_medical_advices = db.scalar(
            select(
                func.count(
                    MedicalAdviceModel.id
                )
            )
        )

        total_reports = db.scalar(
            select(
                func.count(
                    ReportModel.id
                )
            )
        )

        return {
            "total_users":
                int(total_users or 0),
            "active_users":
                int(active_users or 0),
            "total_patients":
                int(total_patients or 0),
            "total_analyses":
                int(total_analyses or 0),
            "completed_analyses":
                int(
                    completed_analyses or 0
                ),
            "failed_analyses":
                int(failed_analyses or 0),
            "total_medical_advices":
                int(
                    total_medical_advices
                    or 0
                ),
            "total_reports":
                int(total_reports or 0),
        }

    def get_prediction_distribution(
        self,
        db: Session,
    ) -> list[dict]:

        count_expression = func.count(
            PredictionModel.id
        )

        statement = (
            select(
                PredictionModel
                .predicted_class,
                count_expression.label(
                    "prediction_count"
                ),
            )
            .group_by(
                PredictionModel
                .predicted_class
            )
            .order_by(
                count_expression.desc(),
                PredictionModel
                .predicted_class.asc(),
            )
        )

        rows = db.execute(
            statement
        ).all()

        return [
            {
                "class_name":
                    row.predicted_class,
                "count":
                    int(
                        row.prediction_count
                    ),
            }
            for row in rows
        ]

    def get_model_usage(
        self,
        db: Session,
    ) -> list[dict]:

        count_expression = func.count(
            AnalysisModel.id
        )

        statement = (
            select(
                AIModel.model_key,
                AIModel.display_name,
                AIModel.version,
                count_expression.label(
                    "analysis_count"
                ),
            )
            .join(
                AnalysisModel,
                AnalysisModel.model_id
                == AIModel.id,
            )
            .group_by(
                AIModel.id,
                AIModel.model_key,
                AIModel.display_name,
                AIModel.version,
            )
            .order_by(
                count_expression.desc(),
                AIModel.model_key.asc(),
                AIModel.version.asc(),
            )
        )

        rows = db.execute(
            statement
        ).all()

        return [
            {
                "model_key":
                    row.model_key,
                "display_name":
                    row.display_name,
                "version":
                    row.version,
                "analysis_count":
                    int(
                        row.analysis_count
                    ),
            }
            for row in rows
        ]

    def list_recent_analyses(
        self,
        db: Session,
        *,
        limit: int = 10,
    ) -> list[dict]:

        statement = (
            select(
                AnalysisModel.id.label(
                    "analysis_id"
                ),
                AnalysisModel
                .analysis_code,
                PatientProfileModel
                .patient_code,
                AnalysisModel.status,
                AIModel.model_key,
                AIModel.version.label(
                    "model_version"
                ),
                PredictionModel
                .predicted_class,
                PredictionModel
                .confidence,
                AnalysisModel.created_at,
            )
            .join(
                PatientProfileModel,
                AnalysisModel.patient_id
                == PatientProfileModel.id,
            )
            .join(
                AIModel,
                AnalysisModel.model_id
                == AIModel.id,
            )
            .outerjoin(
                PredictionModel,
                PredictionModel.analysis_id
                == AnalysisModel.id,
            )
            .order_by(
                AnalysisModel
                .created_at.desc(),
                AnalysisModel.id.desc(),
            )
            .limit(limit)
        )

        rows = db.execute(
            statement
        ).mappings().all()

        return [
            dict(row)
            for row in rows
        ]
