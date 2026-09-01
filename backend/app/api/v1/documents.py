"""Document upload/import endpoints (Phase 10) — the real REST surface that
feeds Phase 9's vector-store pipeline. Uploads/imports return immediately
with the document in `pending` status; a Celery task
(app/workers/tasks.py::process_document_task) does the actual extraction/
chunking/embedding, matching the research-session flow's
queued-now-processed-async shape (app/api/v1/sessions.py).
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_current_user, get_knowledge_base_service
from app.models.document import Document, DocumentSourceType
from app.models.user import User
from app.schemas.document import DocumentRead, DocumentReadWithChunkCount, ImportUrlRequest
from app.services.exceptions import DocumentNotFoundError, ProjectNotFoundError
from app.services.knowledge_base_service import KnowledgeBaseService
from app.workers.celery_app import celery_app

router = APIRouter()

_EXTENSION_TO_SOURCE_TYPE: dict[str, DocumentSourceType] = {
    "pdf": "pdf",
    "docx": "docx",
    "txt": "txt",
    "csv": "csv",
    "md": "markdown",
    "markdown": "markdown",
}
_YOUTUBE_HOSTS = ("youtube.com", "youtu.be")


def _source_type_for_filename(filename: str) -> DocumentSourceType:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    source_type = _EXTENSION_TO_SOURCE_TYPE.get(extension)
    if source_type is None:
        supported = ", ".join(sorted(set(_EXTENSION_TO_SOURCE_TYPE)))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"unsupported file extension {extension!r} — supported: {supported}",
        )
    return source_type


def _source_type_for_url(url: str) -> DocumentSourceType:
    return "youtube" if any(host in url for host in _YOUTUBE_HOSTS) else "url"


@router.post("/documents/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> Document:
    source_type = _source_type_for_filename(file.filename or "")
    content = await file.read()
    try:
        document = await service.upload_document(
            project_id, current_user.id, file.filename or "upload", source_type, content
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc

    celery_app.send_task("knowledge_base.process_document", args=[str(document.id)])
    return document


@router.post(
    "/documents/import-url", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
async def import_url(
    body: ImportUrlRequest,
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> Document:
    source_type = _source_type_for_url(body.url)
    try:
        document = await service.import_url(
            body.project_id, current_user.id, body.url, source_type
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc

    celery_app.send_task("knowledge_base.process_document", args=[str(document.id)])
    return document


@router.get("/documents/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> Document:
    try:
        return await service.get_document(document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> None:
    try:
        await service.delete_document(document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc


@router.get("/projects/{project_id}/documents", response_model=list[DocumentReadWithChunkCount])
async def list_project_documents(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_base_service),
) -> list[DocumentReadWithChunkCount]:
    try:
        pairs = await service.list_documents(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from exc

    return [
        DocumentReadWithChunkCount(
            id=document.id,
            project_id=document.project_id,
            source_type=document.source_type,
            original_filename=document.original_filename,
            status=document.status,
            created_at=document.created_at,
            chunk_count=chunk_count,
        )
        for document, chunk_count in pairs
    ]
