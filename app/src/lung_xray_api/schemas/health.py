"""Schemas health check."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    model_ready: bool | None = None
    model_version: str | None = None
