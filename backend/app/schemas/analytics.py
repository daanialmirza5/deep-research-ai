from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SessionsOverTimePoint(BaseModel):
    date: str
    count: int


class AgentRejectionRate(BaseModel):
    agent_name: str
    rejection_rate: float
    total_runs: int


class AnalyticsOverview(BaseModel):
    sessions_run: int
    avg_completion_seconds: float | None
    success_rate: float
    sessions_over_time: list[SessionsOverTimePoint]
    agent_rejection_rates: list[AgentRejectionRate]


class UsageByAgent(BaseModel):
    agent_name: str
    call_count: int
    prompt_tokens: int
    completion_tokens: int


class AnalyticsUsage(BaseModel):
    usage_by_agent: list[UsageByAgent]


class RecentActivityItem(BaseModel):
    event_type: str
    payload: dict[str, Any] | None
    created_at: datetime
