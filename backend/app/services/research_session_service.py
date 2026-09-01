import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.report import Report
from app.models.research_session import ResearchSession
from app.repositories.analytics_event import AnalyticsEventRepository
from app.repositories.research_session import ResearchSessionRepository
from app.services.exceptions import ResearchSessionNotFoundError
from app.services.project_service import ProjectService


class ResearchSessionService:
    def __init__(self, session: AsyncSession, project_service: ProjectService) -> None:
        self.sessions = ResearchSessionRepository(session)
        self.projects = project_service
        self.analytics_events = AnalyticsEventRepository(session)

    async def create_session(
        self, project_id: uuid.UUID, user_id: uuid.UUID, query: str
    ) -> ResearchSession:
        # Raises ProjectNotFoundError (a distinct exception the router maps
        # to its own 404) if the project doesn't exist or isn't the user's.
        await self.projects.get_project(project_id, user_id)
        # See app/services/auth_service.py's register() comment: a freshly
        # constructed model's client-side-default id is None until flush.
        session_uuid = uuid.uuid4()
        research_session = ResearchSession(
            id=session_uuid,
            project_id=project_id,
            user_id=user_id,
            query=query,
            status="queued",
            revision_count=0,
        )
        self.analytics_events.record("session.created", user_id=user_id, session_id=session_uuid)
        return await self.sessions.create(research_session)

    async def list_sessions(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[ResearchSession]:
        await self.projects.get_project(project_id, user_id)
        return await self.sessions.list_for_project(project_id)

    async def get_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> ResearchSession:
        research_session = await self.sessions.get_by_id(session_id)
        if (
            research_session is None
            or research_session.deleted_at is not None
            or research_session.user_id != user_id
        ):
            raise ResearchSessionNotFoundError(session_id)
        return research_session

    async def list_messages(self, session_id: uuid.UUID, user_id: uuid.UUID) -> list[Message]:
        await self.get_session(session_id, user_id)
        return await self.sessions.list_messages(session_id)

    async def get_latest_report(self, session_id: uuid.UUID, user_id: uuid.UUID) -> Report | None:
        await self.get_session(session_id, user_id)
        return await self.sessions.get_latest_report(session_id)
