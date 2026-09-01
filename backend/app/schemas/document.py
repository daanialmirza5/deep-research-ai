import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_type: str
    original_filename: str | None
    status: str
    created_at: datetime


class DocumentReadWithChunkCount(DocumentRead):
    chunk_count: int


class ImportUrlRequest(BaseModel):
    project_id: uuid.UUID
    url: str = Field(min_length=1, max_length=2000)
