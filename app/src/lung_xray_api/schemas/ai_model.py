from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_key: str
    display_name: str
    architecture: str
    version: str
    class_names: list[str]
    is_active: bool
    is_default: bool
    created_at: datetime