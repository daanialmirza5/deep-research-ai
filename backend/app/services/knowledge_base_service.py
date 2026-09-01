"""Real document ingestion + cosine-similarity search over a project's
knowledge base — the Phase 9/10 vector-store pipeline.

Two ways in:
  - `upload_document`/`import_url` + `process_document`: the real Phase 10
    path. The router stores raw bytes (file uploads) or the source URL
    (url/youtube imports) and creates a `pending` Document row synchronously;
    a Celery task (app/workers/tasks.py::process_document_task) then calls
    `process_document`, which fetches the raw content back, runs the
    format-specific loader (ai/loaders/), chunks, embeds, and indexes it.
  - `ingest_text`: Phase 9's original shortcut for already-extracted plain
    text (no loader, no storage involved) — kept for callers that already
    have text in hand (tests, and anything that doesn't need a loader).
Both funnel into `_chunk_and_index` so the chunk/embed/persist/status logic
lives in exactly one place.
"""

import uuid

from ai.chunking import chunk_text
from ai.embeddings.base import EmbeddingProvider
from ai.loaders.base import LoaderError
from ai.loaders.registry import get_loader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.object_storage import ObjectStorage
from app.models.document import Document, DocumentSourceType
from app.repositories.analytics_event import AnalyticsEventRepository
from app.repositories.document import DocumentRepository
from app.repositories.embedding import EmbeddingRepository
from app.schemas.knowledge_base import SearchResult
from app.services.exceptions import DocumentNotFoundError, ProjectNotFoundError
from app.services.project_service import ProjectService

# Loaders that read raw file bytes out of object storage; the rest (url,
# youtube) have no uploaded file at all — storage_path holds the source URL
# itself, fetched fresh at processing time instead.
_FILE_BASED_SOURCE_TYPES = {"pdf", "docx", "txt", "csv", "markdown"}


class KnowledgeBaseService:
    def __init__(
        self,
        session: AsyncSession,
        embeddings: EmbeddingProvider,
        object_storage: ObjectStorage,
        project_service: ProjectService,
    ) -> None:
        self.session = session
        self.documents = DocumentRepository(session)
        self.embeddings_repo = EmbeddingRepository(session)
        self.analytics_events = AnalyticsEventRepository(session)
        self._embeddings = embeddings
        self._object_storage = object_storage
        self.projects = project_service

    async def upload_document(
        self,
        project_id: uuid.UUID,
        uploader_id: uuid.UUID,
        filename: str,
        source_type: DocumentSourceType,
        content: bytes,
    ) -> Document:
        # Raises ProjectNotFoundError (the router maps it to 404) if the
        # project doesn't exist or isn't the caller's.
        await self.projects.get_project(project_id, uploader_id)
        storage_key = f"{project_id}/{uuid.uuid4()}-{filename}"
        await self._object_storage.upload(storage_key, content)
        # See app/services/auth_service.py's register() comment: a freshly
        # constructed model's client-side-default id is None until flush.
        document_id = uuid.uuid4()
        document = Document(
            id=document_id,
            project_id=project_id,
            uploaded_by=uploader_id,
            source_type=source_type,
            original_filename=filename,
            storage_path=storage_key,
            status="pending",
        )
        self.analytics_events.record(
            "document.uploaded",
            user_id=uploader_id,
            payload={"document_id": str(document_id), "source_type": source_type},
        )
        return await self.documents.create(document)

    async def import_url(
        self,
        project_id: uuid.UUID,
        uploader_id: uuid.UUID,
        url: str,
        source_type: DocumentSourceType,
    ) -> Document:
        await self.projects.get_project(project_id, uploader_id)
        document_id = uuid.uuid4()
        document = Document(
            id=document_id,
            project_id=project_id,
            uploaded_by=uploader_id,
            source_type=source_type,
            original_filename=url,
            storage_path=url,
            status="pending",
        )
        self.analytics_events.record(
            "document.imported",
            user_id=uploader_id,
            payload={"document_id": str(document_id), "source_type": source_type},
        )
        return await self.documents.create(document)

    async def process_document(self, document_id: uuid.UUID) -> Document:
        document = await self.documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)

        document.status = "processing"
        await self.session.commit()

        try:
            raw_content: bytes | str
            if document.source_type in _FILE_BASED_SOURCE_TYPES:
                raw_content = await self._object_storage.download(document.storage_path)
            else:
                raw_content = document.storage_path
            text = await get_loader(document.source_type).load(raw_content)
        except LoaderError as exc:
            document.status = "failed"
            self.analytics_events.record(
                "document.failed",
                user_id=document.uploaded_by,
                payload={"document_id": str(document.id), "detail": str(exc)},
            )
            await self.session.commit()
            raise

        await self._chunk_and_index(document, text)
        return document

    async def ingest_text(
        self,
        project_id: uuid.UUID,
        uploader_id: uuid.UUID,
        filename: str,
        source_type: DocumentSourceType,
        text: str,
    ) -> Document:
        await self.projects.get_project(project_id, uploader_id)
        document = Document(
            project_id=project_id,
            uploaded_by=uploader_id,
            source_type=source_type,
            # No object storage for already-in-hand text — a marker, not a
            # real storage key (contrast upload_document, which stores real
            # bytes before this ever runs).
            storage_path=f"inline-text://{filename}",
            original_filename=filename,
            status="processing",
        )
        self.session.add(document)
        await self.session.flush()

        await self._chunk_and_index(document, text)
        return document

    async def list_documents(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[tuple[Document, int]]:
        await self.projects.get_project(project_id, user_id)
        return await self.documents.list_for_project(project_id)

    async def get_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> Document:
        document = await self.documents.get_by_id(document_id)
        if document is None or document.deleted_at is not None:
            raise DocumentNotFoundError(document_id)
        try:
            await self.projects.get_project(document.project_id, user_id)
        except ProjectNotFoundError as exc:
            # Same non-disclosure posture as ProjectService.get_project: a
            # document belonging to someone else's project reports the same
            # 404 as one that doesn't exist at all.
            raise DocumentNotFoundError(document_id) from exc
        return document

    async def delete_document(self, document_id: uuid.UUID, user_id: uuid.UUID) -> None:
        document = await self.get_document(document_id, user_id)
        await self.documents.soft_delete(document)

    async def _chunk_and_index(self, document: Document, text: str) -> None:
        chunks = chunk_text(text)
        if chunks:
            vectors = await self._embeddings.embed(chunks)
            await self.embeddings_repo.create_many(document.id, chunks, vectors)
        document.status = "indexed" if chunks else "failed"
        self.analytics_events.record(
            f"document.{document.status}",
            user_id=document.uploaded_by,
            payload={"document_id": str(document.id), "chunk_count": len(chunks)},
        )
        await self.session.commit()
        await self.session.refresh(document)

    async def search(
        self, project_id: uuid.UUID, user_id: uuid.UUID, query: str, *, top_k: int = 5
    ) -> list[SearchResult]:
        await self.projects.get_project(project_id, user_id)
        [query_vector] = await self._embeddings.embed([query])
        pairs = await self.embeddings_repo.similarity_search(project_id, query_vector, top_k=top_k)
        return [
            SearchResult(
                document_id=embedding.document_id,
                chunk_index=embedding.chunk_index,
                chunk_text=embedding.chunk_text,
                score=1.0 - distance,
            )
            for embedding, distance in pairs
        ]
