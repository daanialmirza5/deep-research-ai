"""FastAPI `Depends()`-compatible providers. Kept separate from
app.core.container so container <-> db imports stay one-directional (see
app/core/db.py's docstring) — this module is the only place that reaches into
`request.app.state.container`, and only route handlers import it.

Auth is deliberately implemented as a dependency (`get_current_user`), not a
blanket ASGI middleware: several routes are intentionally public (register,
login, health, docs, OAuth entrypoints), and a middleware would need its own
path-based allowlist to skip them — more fragile than each route declaring
what it needs via `Depends(...)`, which is also what FastAPI's own docs
recommend for this reason.
"""

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.container import Container
from app.core.exceptions import InvalidTokenError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.project_service import ProjectService
from app.services.research_session_service import ResearchSessionService

_bearer_scheme = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container  # type: ignore[no-any-return]


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    container = request.app.state.container
    async with container.db_sessionmaker() as session:
        yield session


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(session=session, settings=settings)


def get_project_service(session: AsyncSession = Depends(get_db_session)) -> ProjectService:
    return ProjectService(session)


def get_research_session_service(
    session: AsyncSession = Depends(get_db_session),
) -> ResearchSessionService:
    return ResearchSessionService(session, ProjectService(session))


def get_knowledge_base_service(
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_container),
) -> KnowledgeBaseService:
    # container.embeddings is a lazy cached_property (app/core/container.py) —
    # the first real call from this process is what actually imports the
    # configured provider. With the default EMBEDDING_PROVIDER=bge that means
    # sentence-transformers/torch, which docker/backend/Dockerfile deliberately
    # doesn't install (see its docstring) — this endpoint's existence means
    # that "lean API image" assumption needs revisiting in Phase 13, not
    # something to work around here.
    return KnowledgeBaseService(
        session, container.embeddings, container.object_storage, ProjectService(session)
    )


def get_analytics_service(session: AsyncSession = Depends(get_db_session)) -> AnalyticsService:
    return AnalyticsService(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except InvalidTokenError as exc:
        raise unauthorized from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
