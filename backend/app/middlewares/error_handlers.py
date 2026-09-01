"""Global exception handlers producing RFC 7807 problem+json bodies for every
error path (HTTP exceptions, request validation, and unhandled exceptions),
per the error convention in docs/api-design.md § conventions.
"""

from collections.abc import Mapping

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger("app.error")

PROBLEM_JSON = "application/problem+json"


def _problem(
    status_code: int,
    title: str,
    detail: str,
    instance: str,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type=PROBLEM_JSON,
        headers=dict(headers) if headers else None,
        content={
            "type": "about:blank",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": instance,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        # exc.headers matters for e.g. WWW-Authenticate on 401s (see
        # app/api/deps.py's get_current_user) — dropping it here would
        # silently discard headers the raiser deliberately set.
        return _problem(
            exc.status_code,
            "HTTPException",
            str(exc.detail),
            str(request.url.path),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "ValidationError",
            str(exc.errors()),
            str(request.url.path),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=exc)
        return _problem(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "InternalServerError",
            "An unexpected error occurred.",
            str(request.url.path),
        )
