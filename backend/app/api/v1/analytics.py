"""Real aggregation endpoints (Phase 11) for the Analytics Dashboard — no
mock data. Scoped to the current user across all their projects/sessions
(see app/services/analytics_service.py's docstring for why there's no
per-project filter here, unlike Knowledge Base search).
"""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_analytics_service, get_current_user
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview, AnalyticsUsage, RecentActivityItem
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/analytics/overview", response_model=AnalyticsOverview)
async def get_overview(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsOverview:
    return await service.get_overview(current_user.id, days=days)


@router.get("/analytics/usage", response_model=AnalyticsUsage)
async def get_usage(
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsUsage:
    return await service.get_usage(current_user.id, days=days)


@router.get("/analytics/activity", response_model=list[RecentActivityItem])
async def get_recent_activity(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> list[RecentActivityItem]:
    return await service.get_recent_activity(current_user.id, limit=limit)
