"""Token-bucket rate limiting (see docs/api-design.md § conventions). The
default limit applies globally; individual routes override it with a
`@limiter.limit(...)` decorator once they exist (e.g. Phase 5's stricter
10/minute on POST /auth/login).

Storage is in-memory (slowapi's default), which is per-process — fine for a
single-instance deployment or local dev. Multi-replica production deployments
should point this at Redis (`storage_uri=settings.redis_url`) in Phase 13;
noted here rather than done now since it's a one-line change with no other
Phase 3 code depending on it.
"""

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


async def rate_limit_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    # Registered via app.add_exception_handler(RateLimitExceeded, ...), so this
    # is only ever invoked for that type; the broader `Exception` parameter type
    # matches Starlette's exception-handler signature exactly (strict mypy).
    assert isinstance(exc, RateLimitExceeded)
    return JSONResponse(
        status_code=429,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "title": "RateLimitExceeded",
            "status": 429,
            "detail": str(exc.detail),
            "instance": str(request.url.path),
        },
    )
