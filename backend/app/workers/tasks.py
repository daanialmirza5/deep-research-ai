"""Celery task that runs the LangGraph research pipeline end-to-end for one
ResearchSession: builds the graph (ai/graph/build.py), streams node-by-node
updates, persists an AgentRun + Message row per step, republishes each step
over Redis pub/sub for app/api/ws.py to relay to the browser, and persists
the final Report + Citation rows.

One Container per worker process (see app/core/container.py's docstring) —
built lazily on first task invocation via _get_container(), not at module
import time, so importing this module (Celery's autodiscovery does this at
startup) never requires a live DB/Redis connection.
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from ai.graph.build import build_research_graph
from ai.graph.state import ResearchState
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.container import Container, build_container
from app.core.pubsub import publish_event
from app.models.agent import Agent, AgentRun
from app.models.message import Message
from app.models.report import Citation, Report
from app.models.research_session import ResearchSession
from app.repositories.analytics_event import AnalyticsEventRepository
from app.repositories.embedding import EmbeddingRepository
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.pg_vector_store import PgVectorStore
from app.services.project_service import ProjectService
from app.workers.celery_app import celery_app

# Mirrors the Annotated[list, operator.add] fields in ai/graph/state.py.
# graph.astream(..., stream_mode="updates") yields each node's raw return
# value, not the graph's internally-reduced state, so for these fields that's
# the *new* items only (verified directly: a node re-entered via a revision
# loop returns just its own findings/messages, not the running total). We
# replicate LangGraph's own operator.add reducer here so the state we persist
# as ResearchSession.graph_state matches what graph.ainvoke() would return.
_ACCUMULATING_FIELDS = {"messages", "errors", "research_findings", "retrieved_context"}

_container: Container | None = None


def _get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


async def _release_event_loop_bound_connections(container: Container) -> None:
    """Each task entrypoint (run_research_pipeline/process_document_task)
    wraps its async body in its own `asyncio.run(...)`, which tears down that
    call's event loop when it returns — but `_container` (and its db_engine's
    connection pool, and its redis client) is a module global reused across
    every task this worker process ever runs. A pooled asyncpg connection is
    bound to the loop it was created on; without disposing here, the *next*
    task's (new) event loop can be handed a connection from this task's
    (now-closed) loop and crash with `AttributeError: 'NoneType' object has
    no attribute 'send'` deep in asyncpg — caught live via a real Celery
    worker processing two documents back to back, not by any single-task test
    in isolation.

    `container.redis` has the exact same defect: redis-py lazily opens its
    first real socket on first command, binding it to whichever loop is
    running then. `_run_pipeline_async` is the only task body that actually
    uses `container.redis` (via publish_event) — process_document_task never
    calls it — so this went uncaught until two real (not fakeredis) research
    pipeline runs executed back to back against the same persistent worker
    process, the second one crashing with `RuntimeError: Event loop is
    closed` deep in redis-py's connection teardown. `aclose()` disconnects
    the pool without discarding the `Redis` object itself, so the same
    `container.redis` instance transparently reconnects on the next task's
    new loop — matching `db_engine.dispose()`'s behavior exactly.

    `container.llm` has the same root cause a third time: every `LLMProvider`
    (OpenAI/Anthropic/Ollama — see `ai/llm/*_provider.py`) wraps its vendor
    SDK's own async, httpx-based client, constructed once and cached
    (`functools.cached_property`) for the worker's lifetime. Unlike
    db_engine/redis, an SDK client exposes no cross-loop-safe "reconnect" —
    so instead of closing it, we drop the cached_property entirely; the next
    task's first `container.llm` access rebuilds a fresh provider (and a
    fresh, unopened client bound to *its* loop) via `get_llm_provider`.
    Constructing a vendor client has no network cost — the actual connection
    opens lazily on first request — so this is free. `container.embeddings`
    is deliberately left alone: the default local BGE provider has no
    persistent async client to go stale (`asyncio.to_thread` around a
    synchronous, in-process model — see `ai/embeddings/bge_provider.py`), and
    resetting it unconditionally would force a multi-second model reload on
    every single task, including every `knowledge_base.process_document_task`
    call. Caught the same way as the redis bug: the second of two real
    pipeline runs against one worker process crashed mid-`planner`-node with
    `RuntimeError: Event loop is closed` deep in httpcore this time, not
    redis-py.
    """
    await container.db_engine.dispose()
    await container.redis.aclose()
    if "llm" in container.__dict__:
        del container.__dict__["llm"]


def _merge_state(state: dict[str, Any], node_output: dict[str, Any]) -> None:
    for key, value in node_output.items():
        if key in _ACCUMULATING_FIELDS:
            state[key] = [*state.get(key, []), *value]
        else:
            state[key] = value


@celery_app.task(name="research.run_pipeline")  # type: ignore[untyped-decorator]
def run_research_pipeline(session_id: str) -> None:
    asyncio.run(_run_pipeline_async(uuid.UUID(session_id)))


async def _run_pipeline_async(session_id: uuid.UUID) -> None:
    container = _get_container()
    try:
        async with container.db_sessionmaker() as db:
            research_session = await db.get(ResearchSession, session_id)
            if research_session is None:
                # The row that should have enqueued this task is gone (e.g.
                # deleted between enqueue and pickup) — nothing to report
                # back to, so there's nothing sensible left to do.
                return

            agents_by_name = {
                agent.name: agent
                for agent in (await db.execute(select(Agent))).scalars().all()
            }

            research_session.status = "running"
            research_session.started_at = datetime.now(UTC)
            await db.commit()
            await publish_event(
                container.redis, str(session_id), {"type": "status", "status": "running"}
            )

            analytics_events = AnalyticsEventRepository(db)

            try:
                final_state = await _stream_graph(
                    container, db, research_session, agents_by_name
                )
            except Exception as exc:  # noqa: BLE001 - record failure before propagating
                research_session.status = "failed"
                analytics_events.record(
                    "session.failed",
                    user_id=research_session.user_id,
                    session_id=research_session.id,
                    payload={"detail": str(exc)},
                )
                await db.commit()
                await publish_event(
                    container.redis,
                    str(session_id),
                    {"type": "status", "status": "failed", "detail": str(exc)},
                )
                raise

            await _persist_report(db, research_session, final_state)
            research_session.status = "completed"
            research_session.completed_at = datetime.now(UTC)
            research_session.revision_count = final_state.get("revision_count", 0)
            research_session.graph_state = final_state
            duration_seconds = (
                (research_session.completed_at - research_session.started_at).total_seconds()
                if research_session.started_at
                else None
            )
            analytics_events.record(
                "session.completed",
                user_id=research_session.user_id,
                session_id=research_session.id,
                payload={
                    "duration_seconds": duration_seconds,
                    "revision_count": research_session.revision_count,
                    "quality_score": final_state.get("quality_score"),
                },
            )
            await db.commit()
            await publish_event(
                container.redis, str(session_id), {"type": "status", "status": "completed"}
            )
    finally:
        await _release_event_loop_bound_connections(container)


async def _stream_graph(
    container: Container,
    db: AsyncSession,
    research_session: ResearchSession,
    agents_by_name: dict[str, Agent],
) -> dict[str, Any]:
    graph = build_research_graph(
        container.llm,
        container.embeddings,
        max_revision_loops=container.settings.max_revision_loops,
        vector_store=PgVectorStore(EmbeddingRepository(db)),
    )
    initial_state: ResearchState = {
        "session_id": str(research_session.id),
        "project_id": str(research_session.project_id),
        "query": research_session.query,
        "revision_count": research_session.revision_count,
    }

    final_state: dict[str, Any] = dict(initial_state)
    # Wall-clock time between successive yields, as a proxy for a node's own
    # execution time — plain astream() exposes no per-node start hook, so
    # this is an approximation (it also counts inter-node overhead), not a
    # precise measurement.
    last_step_finished = time.monotonic()

    async for step in graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_output in step.items():
            now = time.monotonic()
            duration_ms = int((now - last_step_finished) * 1000)
            last_step_finished = now

            _merge_state(final_state, node_output)

            agent = agents_by_name.get(node_name)
            if agent is None:
                raise RuntimeError(
                    f"no seeded Agent row named {node_name!r} — run "
                    "app/scripts/seed.py before submitting research sessions"
                )

            db.add(
                AgentRun(
                    session_id=research_session.id,
                    agent_id=agent.id,
                    status="completed",
                    output_state={k: v for k, v in node_output.items() if k != "messages"},
                    duration_ms=duration_ms,
                )
            )
            for text in node_output.get("messages", []):
                db.add(
                    Message(
                        session_id=research_session.id,
                        role="agent",
                        content=text,
                        agent_metadata={"node": node_name},
                    )
                )
            await db.commit()

            await publish_event(
                container.redis,
                str(research_session.id),
                {
                    "type": "node_update",
                    "node": node_name,
                    "messages": node_output.get("messages", []),
                },
            )

    return final_state


async def _persist_report(
    db: AsyncSession, research_session: ResearchSession, final_state: dict[str, Any]
) -> None:
    report = Report(
        session_id=research_session.id,
        title=research_session.query[:500],
        content_markdown=final_state.get("draft_report", ""),
        quality_score=final_state.get("quality_score"),
        status="approved" if final_state.get("review_approved") else "draft",
        version=final_state.get("revision_count", 0) + 1,
    )
    db.add(report)
    await db.flush()

    for citation in final_state.get("citations", []):
        db.add(
            Citation(
                report_id=report.id,
                source_type=citation.get("source_type", "unknown"),
                title=citation.get("title", "(untitled)")[:1000],
                url=citation.get("url"),
            )
        )


@celery_app.task(name="knowledge_base.process_document")  # type: ignore[untyped-decorator]
def process_document_task(document_id: str) -> None:
    asyncio.run(_process_document_async(uuid.UUID(document_id)))


async def _process_document_async(document_id: uuid.UUID) -> None:
    container = _get_container()
    try:
        async with container.db_sessionmaker() as db:
            service = KnowledgeBaseService(
                db, container.embeddings, container.object_storage, ProjectService(db)
            )
            try:
                await service.process_document(document_id)
            except Exception:  # noqa: BLE001 - ensure the document never gets stuck "processing"
                # process_document already marks LoaderError failures itself;
                # this catches anything else (DB/embedding-provider errors) too.
                document = await service.documents.get_by_id(document_id)
                if document is not None and document.status == "processing":
                    document.status = "failed"
                    await db.commit()
                raise
    finally:
        await _release_event_loop_bound_connections(container)
