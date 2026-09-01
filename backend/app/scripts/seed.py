"""Development seed data. Currently just the `agents` reference table (see
database/seeds/README.md) — one row per agent type, matching
ai.graph.state.AgentName exactly. Run via `make seed`. Idempotent: safe to
run against a database that's already seeded.
"""

import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.models.agent import Agent

AGENT_SEEDS: list[tuple[str, str, str]] = [
    ("planner", "planner", "Creates the execution strategy for a research query."),
    ("research", "research", "Searches web, Arxiv, Semantic Scholar, Crossref, Wikipedia, GitHub."),
    ("retriever", "retriever", "Searches the project's vector-embedded knowledge base."),
    ("summarizer", "summarizer", "Compresses research findings and retrieved context."),
    ("fact_checker", "fact_checker", "Verifies claims against retrieved sources."),
    ("writer", "writer", "Writes the research report."),
    ("reviewer", "reviewer", "Reviews and critiques the draft report, requesting revisions."),
    ("citation", "citation", "Generates formatted citations for cited sources."),
    ("evaluation", "evaluation", "Scores the finished report's quality."),
    ("memory", "memory", "Persists the finished session to the long-term knowledge base."),
]


async def seed_agents() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    sessionmaker = create_session_factory(engine)

    inserted = 0
    async with sessionmaker() as session:
        for name, agent_type, description in AGENT_SEEDS:
            existing = (
                await session.execute(select(Agent).where(Agent.name == name))
            ).scalar_one_or_none()
            if existing is not None:
                continue
            session.add(Agent(name=name, type=agent_type, description=description))
            inserted += 1
        await session.commit()

    await engine.dispose()
    print(f"Seeded {inserted} agent(s); {len(AGENT_SEEDS) - inserted} already present.")


if __name__ == "__main__":
    asyncio.run(seed_agents())
