"""Real (non-mock) aggregation queries over research_sessions/agent_runs for
the Analytics Dashboard (Phase 11). Scoped to the current user across all
their projects — the dashboard has no per-project selector (see
docs/ui-wireframes.md § 9), unlike the Knowledge Base page.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentRun
from app.models.analytics_event import AnalyticsEvent
from app.models.research_session import ResearchSession
from app.schemas.analytics import (
    AgentRejectionRate,
    AnalyticsOverview,
    AnalyticsUsage,
    RecentActivityItem,
    SessionsOverTimePoint,
    UsageByAgent,
)

# Which agents gate revisions, and which of their own output_state field/value
# records a rejection — both are already-persisted, real data (no new
# tracking needed). A "rejection" here means the quality gate sent the draft
# back for another pass, not that the agent crashed: Phase 8 never persists a
# per-node crash (a whole session just gets marked "failed" — see
# docs/architecture.md § 6), so a literal crash-rate-by-agent chart isn't
# derivable from what's actually recorded today.
_REJECTION_GATES: dict[str, tuple[str, str]] = {
    "fact_checker": ("fact_check_verdict", "unverified"),
    "reviewer": ("review_approved", "false"),
}


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_overview(self, user_id: uuid.UUID, *, days: int = 30) -> AnalyticsOverview:
        since = datetime.now(UTC) - timedelta(days=days)
        own_recent_sessions = (
            ResearchSession.user_id == user_id,
            ResearchSession.created_at >= since,
            ResearchSession.deleted_at.is_(None),
        )

        sessions_run = (
            await self.session.execute(select(func.count()).where(*own_recent_sessions))
        ).scalar_one()

        avg_completion_seconds = (
            await self.session.execute(
                select(
                    func.avg(
                        func.extract(
                            "epoch", ResearchSession.completed_at - ResearchSession.started_at
                        )
                    )
                ).where(*own_recent_sessions, ResearchSession.status == "completed")
            )
        ).scalar_one()

        completed_count, failed_count = (
            await self.session.execute(
                select(
                    func.count().filter(ResearchSession.status == "completed"),
                    func.count().filter(ResearchSession.status == "failed"),
                ).where(*own_recent_sessions)
            )
        ).one()
        terminal = completed_count + failed_count
        success_rate = (completed_count / terminal) if terminal else 0.0

        day = func.date(ResearchSession.created_at)
        sessions_over_time_rows = (
            await self.session.execute(
                select(day.label("day"), func.count())
                .where(*own_recent_sessions)
                .group_by(day)
                .order_by(day)
            )
        ).all()
        sessions_over_time = [
            SessionsOverTimePoint(date=row.day.isoformat(), count=row[1])
            for row in sessions_over_time_rows
        ]

        agent_rejection_rates = []
        for agent_name, (field, rejected_text) in _REJECTION_GATES.items():
            total, rejected = (
                await self.session.execute(
                    select(
                        func.count(),
                        func.count().filter(AgentRun.output_state[field].astext == rejected_text),
                    )
                    .select_from(AgentRun)
                    .join(Agent, Agent.id == AgentRun.agent_id)
                    .join(ResearchSession, ResearchSession.id == AgentRun.session_id)
                    .where(
                        Agent.name == agent_name,
                        ResearchSession.user_id == user_id,
                        ResearchSession.created_at >= since,
                    )
                )
            ).one()
            agent_rejection_rates.append(
                AgentRejectionRate(
                    agent_name=agent_name,
                    rejection_rate=(rejected / total) if total else 0.0,
                    total_runs=total,
                )
            )

        return AnalyticsOverview(
            sessions_run=sessions_run,
            avg_completion_seconds=avg_completion_seconds,
            success_rate=success_rate,
            sessions_over_time=sessions_over_time,
            agent_rejection_rates=agent_rejection_rates,
        )

    async def get_usage(self, user_id: uuid.UUID, *, days: int = 30) -> AnalyticsUsage:
        since = datetime.now(UTC) - timedelta(days=days)
        prompt_tokens_expr = AgentRun.output_state["prompt_tokens"].astext.cast(Integer)
        completion_tokens_expr = AgentRun.output_state["completion_tokens"].astext.cast(Integer)

        rows = (
            await self.session.execute(
                select(
                    Agent.name,
                    func.count(),
                    func.coalesce(func.sum(prompt_tokens_expr), 0),
                    func.coalesce(func.sum(completion_tokens_expr), 0),
                )
                .select_from(AgentRun)
                .join(Agent, Agent.id == AgentRun.agent_id)
                .join(ResearchSession, ResearchSession.id == AgentRun.session_id)
                .where(
                    ResearchSession.user_id == user_id,
                    ResearchSession.created_at >= since,
                    AgentRun.output_state.has_key("prompt_tokens"),
                )
                .group_by(Agent.name)
                .order_by(Agent.name)
            )
        ).all()

        usage_by_agent = [
            UsageByAgent(
                agent_name=row[0], call_count=row[1], prompt_tokens=row[2], completion_tokens=row[3]
            )
            for row in rows
        ]
        return AnalyticsUsage(usage_by_agent=usage_by_agent)

    async def get_recent_activity(
        self, user_id: uuid.UUID, *, limit: int = 20
    ) -> list[RecentActivityItem]:
        rows = (
            (
                await self.session.execute(
                    select(AnalyticsEvent)
                    .where(AnalyticsEvent.user_id == user_id)
                    .order_by(AnalyticsEvent.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [
            RecentActivityItem(
                event_type=event.event_type, payload=event.payload, created_at=event.created_at
            )
            for event in rows
        ]
