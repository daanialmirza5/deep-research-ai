import uuid

from pydantic import BaseModel


class SearchResult(BaseModel):
    document_id: uuid.UUID
    chunk_index: int
    chunk_text: str
    score: float
