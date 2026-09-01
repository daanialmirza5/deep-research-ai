import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_event import AnalyticsEvent


class AnalyticsEventRepository:
    """Thin wrapper over the generic analytics_events log (see that model's
    docstring for why it's one generic table, not one per metric). `record`
    only `add()`s — it never commits — so callers emit events as part of
    whatever transaction they're already running, instead of each event
    forcing its own round trip."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def record(
        self,
        event_type: str,
        *,
        user_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            AnalyticsEvent(
                user_id=user_id, session_id=session_id, event_type=event_type, payload=payload
            )
        )
