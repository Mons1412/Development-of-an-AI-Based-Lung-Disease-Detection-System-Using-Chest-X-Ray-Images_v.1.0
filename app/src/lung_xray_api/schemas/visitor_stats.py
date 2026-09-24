from uuid import UUID

from pydantic import BaseModel, Field


class VisitorHeartbeatRequest(BaseModel):
    visitor_id: UUID
    session_id: UUID


class VisitorStatsResponse(BaseModel):
    online_now: int = Field(
        ge=0,
    )

    online_today: int = Field(
        ge=0,
    )

    total_visits: int = Field(
        ge=0,
    )
