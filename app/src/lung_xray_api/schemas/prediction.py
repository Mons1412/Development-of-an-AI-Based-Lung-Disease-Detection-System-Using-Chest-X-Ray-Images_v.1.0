"""Schemas prediction response.

Schema giữ cả `probabilities` dạng object và các field probability phẳng để
khớp `inference_contract.json` hiện có trong model package.
"""

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    status: str = Field(default="success")
    prediction: str
    model_probability: float
    probabilities: dict[str, float]
    normal_probability: float
    pneumonia_probability: float
    tuberculosis_probability: float
    model_version: str
    processing_time_ms: int
    disclaimer: str
