from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


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

    @computed_field
    @property
    def summary(self) -> dict[str, str] | None:
        from lung_xray_api.application.services.drai_report import extract_advice_summary
        return extract_advice_summary(self.advice_text)
