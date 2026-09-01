import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    query: str
    status: str
    revision_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    agent_metadata: dict[str, Any] | None
    created_at: datetime


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content_markdown: str
    quality_score: float | None
    status: str
    version: int
    created_at: datetime
