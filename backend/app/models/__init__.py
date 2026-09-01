"""Importing this module registers every model on Base.metadata — required
before Alembic's autogenerate compares the target schema, and before any
relationship() string reference gets resolved. See app/models/base.py for the
shared Base/mixins; alembic/env.py imports this module for exactly this
reason.
"""

from app.models.agent import Agent, AgentRun
from app.models.analytics_event import AnalyticsEvent
from app.models.auth import ApiKey, RefreshToken
from app.models.base import Base
from app.models.document import Document
from app.models.embedding import Embedding
from app.models.message import Message
from app.models.project import Project
from app.models.report import Citation, Report, ReportExport
from app.models.research_session import ResearchSession
from app.models.search_query import SearchQuery
from app.models.user import User

__all__ = [
    "Agent",
    "AgentRun",
    "AnalyticsEvent",
    "ApiKey",
    "Base",
    "Citation",
    "Document",
    "Embedding",
    "Message",
    "Project",
    "RefreshToken",
    "Report",
    "ReportExport",
    "ResearchSession",
    "SearchQuery",
    "User",
]
