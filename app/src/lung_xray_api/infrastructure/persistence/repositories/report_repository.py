from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from lung_xray_api.infrastructure.persistence.orm.analysis_model import (
    AnalysisModel,
)
from lung_xray_api.infrastructure.persistence.orm.report_model import (
    ReportModel,
)


class ReportRepository:

    def create(
        self,
        db: Session,
        *,
        analysis_id: int,
        report_code: str,
        language: str,
        file_path: str,
    ) -> ReportModel:

        report = ReportModel(
            analysis_id=analysis_id,
            report_code=report_code,
            language=language,
            file_path=file_path,
        )

        try:
            db.add(report)
            db.commit()
            db.refresh(report)

            return report

        except Exception:
            db.rollback()
            raise

    def get_by_id(
        self,
        db: Session,
        report_id: int,
    ) -> ReportModel | None:

        statement = (
            select(ReportModel)
            .where(
                ReportModel.id == report_id
            )
            .options(
                selectinload(
                    ReportModel.analysis
                ).selectinload(
                    AnalysisModel.patient
                )
            )
        )

        return db.scalar(statement)

    def get_by_report_code(
        self,
        db: Session,
        report_code: str,
    ) -> ReportModel | None:

        statement = select(
            ReportModel
        ).where(
            ReportModel.report_code == report_code
        )

        return db.scalar(statement)

    def list_by_analysis_id(
        self,
        db: Session,
        analysis_id: int,
    ) -> list[ReportModel]:

        statement = (
            select(ReportModel)
            .where(
                ReportModel.analysis_id == analysis_id
            )
            .order_by(
                ReportModel.created_at.desc(),
                ReportModel.id.desc(),
            )
        )

        return list(
            db.scalars(statement).all()
        )
