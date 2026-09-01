import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        return await self.session.get(Project, project_id)

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id, Project.deleted_at.is_(None))
            .order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())
