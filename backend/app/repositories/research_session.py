import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.report import Report
from app.models.research_session import ResearchSession


class ResearchSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, research_session: ResearchSession) -> ResearchSession:
        self.session.add(research_session)
        await self.session.commit()
        await self.session.refresh(research_session)
        return research_session

    async def get_by_id(self, session_id: uuid.UUID) -> ResearchSession | None:
        return await self.session.get(ResearchSession, session_id)

    async def list_for_project(self, project_id: uuid.UUID) -> list[ResearchSession]:
        result = await self.session.execute(
            select(ResearchSession)
            .where(ResearchSession.project_id == project_id, ResearchSession.deleted_at.is_(None))
            .order_by(ResearchSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_messages(self, session_id: uuid.UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_report(self, session_id: uuid.UUID) -> Report | None:
        result = await self.session.execute(
            select(Report)
            .where(Report.session_id == session_id)
            .order_by(Report.version.desc())
            .limit(1)
        )
        return result.scalars().first()
