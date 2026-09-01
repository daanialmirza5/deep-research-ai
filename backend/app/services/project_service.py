import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.analytics_event import AnalyticsEventRepository
from app.repositories.project import ProjectRepository
from app.services.exceptions import ProjectNotFoundError


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.projects = ProjectRepository(session)
        self.analytics_events = AnalyticsEventRepository(session)

    async def create_project(
        self, owner_id: uuid.UUID, name: str, description: str | None
    ) -> Project:
        # See app/services/auth_service.py's register() comment: a freshly
        # constructed model's client-side-default id is None until flush, so
        # it's generated here rather than read off `project.id` afterward.
        project_id = uuid.uuid4()
        project = Project(id=project_id, owner_id=owner_id, name=name, description=description)
        self.analytics_events.record(
            "project.created", user_id=owner_id, payload={"project_id": str(project_id)}
        )
        return await self.projects.create(project)

    async def list_projects(self, owner_id: uuid.UUID) -> list[Project]:
        return await self.projects.list_for_owner(owner_id)

    async def get_project(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        project = await self.projects.get_by_id(project_id)
        if project is None or project.deleted_at is not None or project.owner_id != owner_id:
            raise ProjectNotFoundError(project_id)
        return project
