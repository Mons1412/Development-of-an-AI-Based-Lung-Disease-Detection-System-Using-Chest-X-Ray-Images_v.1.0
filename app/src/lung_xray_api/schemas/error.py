"""Schemas lỗi public cho API."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    status: str = Field(default="error")
    code: str
    message: str
