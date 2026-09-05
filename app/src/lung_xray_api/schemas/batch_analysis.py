from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from lung_xray_api.schemas.analysis import (
    AnalysisResponse,
)


class BatchAnalysisItemResponse(BaseModel):
    filename: str

    status: Literal[
        "COMPLETED",
        "REJECTED",
        "FAILED",
    ]

    analysis: AnalysisResponse | None = None

    error: str | None = None


class BatchAnalysisResponse(BaseModel):
    total: int
    completed: int
    rejected: int
    failed: int

    items: list[
        BatchAnalysisItemResponse
    ]