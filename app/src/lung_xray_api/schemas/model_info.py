"""Schemas mô tả model public."""

from typing import Any

from pydantic import BaseModel


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    architecture: str
    classes: list[str]
    input_shape: list[int]
    preprocessing: dict[str, Any]
    metrics: dict[str, Any]
    disclaimer: str
