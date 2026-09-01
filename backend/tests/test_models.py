"""DB-less model tests: importing app.models must not raise (no circular
relationship() references), and the resulting metadata must match
docs/database-schema.md exactly — the two are checked separately so a typo'd
table name fails loudly instead of silently missing from a migration.
"""

from app.models import Base

EXPECTED_TABLES = {
    "users",
    "projects",
    "research_sessions",
    "documents",
    "embeddings",
    "messages",
    "agents",
    "agent_runs",
    "reports",
    "citations",
    "report_exports",
    "search_queries",
    "analytics_events",
    "refresh_tokens",
    "api_keys",
}


def test_all_tables_registered_on_metadata() -> None:
    assert set(Base.metadata.tables.keys()) == EXPECTED_TABLES


def test_mapper_configuration_resolves_all_relationships() -> None:
    # Forces SQLAlchemy to resolve every string-based relationship() forward
    # reference across all 15 models — the real check for "no circular
    # import problems disguised as working code."
    from sqlalchemy.orm import configure_mappers

    configure_mappers()
