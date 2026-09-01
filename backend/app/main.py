"""FastAPI application factory and ASGI entrypoint (`uvicorn app.main:app`).

Wiring order matters: logging is configured before anything else logs,
middlewares are added outermost-first (Starlette applies them in reverse
registration order), and exception handlers are registered before the app
can serve traffic that might trigger them.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import api_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from app.core.container import build_container
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.middlewares.error_handlers import register_exception_handlers
from app.middlewares.request_logging import RequestLoggingMiddleware

settings = get_settings()
configure_logging(settings.environment, settings.log_level)
logger = get_logger("app.lifecycle")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("startup", environment=settings.environment, version=__version__)
    yield
    # Disposes the engine's pooled connections while this process's event loop
    # is still the one they were created on. Without this, tests that each
    # wrap the app in their own TestClient (Starlette spins up a fresh
    # background event loop per `with TestClient(app)` block) leave stale
    # connections from a now-dead loop sitting in the pool for the next
    # TestClient to trip over — caught by running the full integration suite
    # together, not any single test file in isolation.
    await app.state.container.db_engine.dispose()
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="DeepResearch AI API",
        version=__version__,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    app.state.container = build_container()
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    # Required by authlib's Starlette OAuth client to hold the state/nonce
    # between the /oauth/{provider} redirect and its /callback (Google/GitHub
    # login, see app/api/v1/auth.py) — unrelated to user login sessions,
    # which stay stateless (JWT access + hashed refresh tokens).
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router)

    Instrumentator().instrument(app).expose(
        app, endpoint="/api/v1/metrics", include_in_schema=False
    )

    return app


app = create_app()
