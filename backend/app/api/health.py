"""Unversioned liveness endpoint for Docker healthchecks / load balancers —
deliberately outside /api/v1 since infra checks aren't part of the business
API's version contract.
"""

from fastapi import APIRouter

from app import __version__

router = APIRouter(tags=["infra"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
