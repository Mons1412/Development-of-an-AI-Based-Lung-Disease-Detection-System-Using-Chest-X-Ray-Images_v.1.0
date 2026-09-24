from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    analysis_id: int = Field(
        gt=0,
    )

    language: str = Field(
        default="vi",
        min_length=2,
        max_length=10,
    )


class ReportResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    analysis_id: int
    report_code: str
    language: str
    created_at: datetime
