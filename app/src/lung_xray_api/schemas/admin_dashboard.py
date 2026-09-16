from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AdminDashboardOverview(BaseModel):
    total_users: int
    active_users: int
    total_patients: int
    total_analyses: int
    completed_analyses: int
    failed_analyses: int
    total_medical_advices: int
    total_reports: int


class AdminPredictionDistributionItem(BaseModel):
    class_name: str
    count: int


class AdminModelUsageItem(BaseModel):
    model_key: str
    display_name: str
    version: str
    analysis_count: int


class AdminRecentAnalysisItem(BaseModel):
    analysis_id: int
    analysis_code: str
    patient_code: str
    status: str
    model_key: str
    model_version: str
    predicted_class: str | None = None
    confidence: float | None = None
    created_at: datetime


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    overview: AdminDashboardOverview
    prediction_distribution: list[
        AdminPredictionDistributionItem
    ]
    model_usage: list[
        AdminModelUsageItem
    ]
    recent_analyses: list[
        AdminRecentAnalysisItem
    ]
