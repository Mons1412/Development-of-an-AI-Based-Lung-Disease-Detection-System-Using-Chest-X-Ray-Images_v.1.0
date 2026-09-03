from datetime import datetime

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    id: int
    analysis_code: str

    patient_code: str

    model_id: int
    model_key: str
    model_version: str

    input_source: str
    original_filename: str

    status: str

    predicted_class: str | None
    confidence: float | None

    probabilities: dict[str, float] | None

    created_at: datetime
    completed_at: datetime | None