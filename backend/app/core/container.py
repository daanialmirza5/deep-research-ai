"""Application-wide dependency container, assembled once at startup
(see app/main.py: `app.state.container = build_container()`).

This is what makes "every component independently replaceable" concrete
rather than aspirational (see docs/architecture.md § 5): concrete
implementations are selected here, from Settings, and handed out as
attributes — callers depend on the container, never on a specific vendor
SDK import.

Phase 9's VectorStore is deliberately *not* here — pgvector search needs a
live AsyncSession scoped to one request/pipeline run, not a process-lifetime
singleton (see app/services/pg_vector_store.py's docstring). ObjectStorage
(Phase 10) has no such constraint — a boto3 S3 client is safely reused across
requests — so it lives here like `redis` does.

Note: AuthService is NOT on this container — it needs a per-request
AsyncSession (not the shared sessionmaker), so it's constructed per-request
by app/api/deps.py's get_auth_service instead. Only genuinely stateless,
process-lifetime singletons (settings, the DB engine, the OAuth client
registry, the LLM/embedding providers, the Redis client) belong here.

Each process (API, and separately each Celery worker) calls
`build_container()` once for its own instance — `redis`/`db_engine` are
connection pools, not shareable across OS process boundaries, which is
exactly right: the worker publishes pipeline events (app/workers/tasks.py)
and the API relays them over WebSocket (app/api/ws.py) via the same Redis
server, each through its own client.

`llm`/`embeddings` are lazy (`functools.cached_property`, not eagerly built
in `build_container()`) on purpose: the default `embedding_provider=bge`
pulls in sentence-transformers/torch, which only the worker image installs
(see docker/backend/Dockerfile vs docker/worker/Dockerfile — the API image
is deliberately lean). Building it eagerly at API startup would crash the
API container with an ImportError it should never have to care about; a
Container is not a dataclass here for exactly this reason (dataclass fields
are eager).
"""

from functools import cached_property

from ai.embeddings.base import EmbeddingProvider
from ai.embeddings.factory import get_embedding_provider
from ai.llm.base import LLMProvider
from ai.llm.factory import get_llm_provider
from authlib.integrations.starlette_client import OAuth
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.db import create_engine, create_session_factory
from app.core.oauth import build_oauth_registry
from app.core.object_storage import ObjectStorage


class Container:
    def __init__(
        self,
        settings: Settings,
        db_engine: AsyncEngine,
        db_sessionmaker: async_sessionmaker[AsyncSession],
        oauth: OAuth,
        redis: Redis,
    ) -> None:
        self.settings = settings
        self.db_engine = db_engine
        self.db_sessionmaker = db_sessionmaker
        self.oauth = oauth
        self.redis = redis

    @cached_property
    def llm(self) -> LLMProvider:
        return get_llm_provider(self.settings)

    @cached_property
    def embeddings(self) -> EmbeddingProvider:
        return get_embedding_provider(self.settings)

    @cached_property
    def object_storage(self) -> ObjectStorage:
        return ObjectStorage(self.settings)


def build_container() -> Container:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    return Container(
        settings=settings,
        db_engine=engine,
        db_sessionmaker=create_session_factory(engine),
        oauth=build_oauth_registry(settings),
        redis=Redis.from_url(settings.redis_url),
    )
