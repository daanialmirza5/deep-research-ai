"""Real cosine-similarity search over a project's embedded knowledge base
(Phase 9). Document upload/import endpoints that feed this (Phase 10) don't
exist yet — see KnowledgeBaseService.ingest_text, used directly by tests and
by the Retriever agent's wiring (app/workers/tasks.py) until then.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user, get_knowledge_base_service
from app.models.user import User
from app.schemas.knowledge_base import SearchResult
from app.services.exceptions import ProjectNotFoundError
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter()


@router.get("/knowledge-base/search", response_model=list[SearchResult])
async def search_knowledge_base(
    project_id: uuid.UUID,
    q: str = Query(min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> list[SearchResult]:
    try:
        return await service.search(project_id, current_user.id, q, top_k=top_k)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc
