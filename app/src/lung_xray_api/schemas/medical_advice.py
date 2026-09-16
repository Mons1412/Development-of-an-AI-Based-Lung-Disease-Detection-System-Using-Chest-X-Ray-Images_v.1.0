from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MedicalAdviceCreate(BaseModel):
    analysis_id: int = Field(
        gt=0,
    )

    language: str = Field(
        default="vi",
        min_length=2,
        max_length=10,
    )


class MedicalAdviceResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    analysis_id: int
    language: str
    provider: str
    model_name: str | None
    advice_text: str
    created_at: datetime
