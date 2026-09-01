# Changelog

All notable changes to this project are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-07

### Added
- Phase 1: project planning documents (architecture, tech stack, database schema, API design,
  UI wireframes, folder structure, milestones).
- Phase 2: repository initialization — `.gitignore`, `.env.example`, Docker Compose (dev + prod
  override), per-service Dockerfiles, Nginx/Prometheus/Grafana configuration, Makefile, dependency
  manifests, community health files.
- Phase 3: FastAPI backend skeleton — typed `Settings` (config.py), structured logging (structlog),
  a DI container assembled at startup, request-logging middleware, RFC 7807 error handlers,
  slowapi rate limiting, versioned `/api/v1` router mount, `GET /health`, Prometheus metrics at
  `/api/v1/metrics`, and the Celery app instance (`app.workers.celery_app`, no tasks yet). Verified
  live: `uvicorn` boots, `/health` returns 200, `/api/docs` renders, ruff/mypy(strict)/pytest all
  clean.
- Phase 4: Database — SQLAlchemy models for all 15 tables in `docs/database-schema.md`
  (`backend/app/models/`), async engine/session factory wired into the DI container, Alembic
  configured for async (asyncpg) migrations with an autogenerate-friendly setup (naming
  convention, ruff post-write hooks, pgvector-aware migration template), and the first migration
  (`initial schema`, includes `CREATE EXTENSION vector` and an HNSW index on `embeddings.embedding`).
  Verified against a real, disposable Postgres 16 + pgvector instance (not just offline SQL
  review): `alembic upgrade head` / `downgrade base` / re-`upgrade head` all clean, and a full
  insert → query → cascade-delete pass through every model via the ORM. That live test caught and
  fixed a real bug — several parent-side relationships (`User.projects`, `.refresh_tokens`,
  `.api_keys`) were missing `cascade="all, delete-orphan"` + `passive_deletes=True`, so deleting a
  user raised a NOT NULL violation instead of cascading. `database/schema.sql` is a generated
  reference snapshot; `docs/folder-structure.md`'s originally-planned `database/migrations/`
  mirror was dropped as pure duplication (see `database/README.md`).
- Phase 5: Authentication — JWT access tokens + hashed, rotating refresh tokens
  (`app/core/security.py`), registration/login/refresh/logout (`app/services/auth_service.py`,
  `app/api/v1/auth.py`), Google/GitHub OAuth via authlib (`app/core/oauth.py`, registered on the
  DI container), the `get_current_user` protected-route dependency (`app/api/deps.py` — a
  dependency, not a blanket ASGI middleware, so public routes don't need an allowlist), and
  `GET /users/me` as the first protected endpoint. Verified against a real, disposable
  Postgres+pgvector instance by driving the entire flow live over HTTP (curl and a permanent
  `pytest` integration test): register → duplicate-email 409 → login (wrong password 401, correct
  200) → protected endpoint (401 without token + `WWW-Authenticate: Bearer`, 200 with) → refresh
  (rotates; reusing the old token is rejected) → logout → refresh-after-logout rejected. That live
  run caught and fixed two real bugs:
    1. `passlib`'s bcrypt self-test crashes against `bcrypt>=4.1`'s stricter >72-byte handling
       (passlib is effectively unmaintained) — switched to calling `bcrypt` directly.
    2. The global RFC 7807 exception handler (`app/middlewares/error_handlers.py`, Phase 3) dropped
       `HTTPException.headers`, silently discarding `WWW-Authenticate` on 401s.
- Phase 6: Frontend — Next.js App Router shell: landing page, `(auth)` login/register (real
  backend calls, chained register→login), `(dashboard)` shell (sidebar/topbar/`AuthGuard`) with a
  real dashboard home (`GET /users/me`) and honest placeholder pages for Workspace/Knowledge
  Base/Reports/Analytics pending their phases, a working Settings/Appearance page, dark-mode-first
  theming (Tailwind v4 CSS tokens, `next-themes`), a hand-written shadcn-style component set, a
  TanStack Query provider, and an `apiClient` with automatic refresh-token rotation on 401 (shared
  in-flight promise so concurrent 401s don't each trigger their own refresh). Verified beyond
  `npm run build`: a real headless-Chromium (Playwright) session against the actual dev server and
  a live backend+Postgres drove register → dashboard (real user data) → logout → blocked direct
  dashboard access → re-login, now a permanent `tests/e2e/auth-flow.spec.ts`; 8 `vitest` unit tests
  cover token storage and the refresh/retry logic; both light and dark themes checked visually.
  Two real, current-at-the-time tooling incompatibilities fixed along the way: `eslint@10` broke
  `eslint-plugin-react` (bundled in `eslint-config-next`, not yet updated for ESLint 10's rule-context
  API) — pinned `eslint@^9.39.4`, the newest version the toolchain actually supports; and
  TypeScript 6's deprecation of `baseUrl` — dropped it, since `paths` alone resolves relative to
  `tsconfig.json` in modern TypeScript.
- Phase 7: AI Agent Framework — `ai/llm/` (`LLMProvider` ABC + OpenAI/Anthropic/Ollama, each over the
  vendor's native SDK directly rather than LangChain's chat-model abstraction — see
  `docs/tech-stack.md`), `ai/embeddings/` (`EmbeddingProvider` ABC + BGE/OpenAI), `ai/agents/` (10
  agents implementing `BaseAgent`; Planner/Writer make real LLM calls and Retriever a real
  embedding call even at the Phase 7 stub stage, the rest are honest stub passthroughs), and
  `ai/graph/` (LangGraph `StateGraph` wiring all 10 nodes with the fact-check/review revision-loop
  conditional edges, factored into standalone, unit-testable `routing.py` predicates). Seeded the
  `agents` reference table (`backend/app/scripts/seed.py`, `make seed`). `app/core/container.py`'s
  `llm`/`embeddings` are lazy (`functools.cached_property`, not built at startup) specifically so
  the lean API image (no `sentence-transformers`/`torch`) never imports them unless something
  actually touches `container.embeddings` — proved this holds by booting the app with those
  imports hard-blocked.
  Had no OpenAI/Anthropic credentials available, so — with explicit sign-off — installed Ollama
  locally (`llama3.2:1b`) as a genuinely live, free LLM provider, and verified the BGE embedding
  provider live too (real `sentence-transformers` model, no credentials needed). Ran the actual
  exit criterion by hand: `build_research_graph()` with real (not fake) Ollama + BGE providers,
  executing start-to-finish through all 10 nodes — real plan and draft-report text back from
  Ollama, a real 384-dim embedding from BGE. 28 tests pass (unit tests with fakes for fast/offline
  coverage, plus the live Ollama/BGE tests), ruff/mypy(strict) clean.
  Two real bugs caught along the way:
    1. A circular import: `ai.agents.base` imports `ai.graph.state`, which — because Python always
       runs a package's `__init__.py` before reaching any of its submodules — pulled in
       `ai/graph/__init__.py`, which re-exported `build_research_graph` from `ai.graph.build`, which
       imports `ai.agents` (still mid-import). Fixed by keeping `ai/graph/__init__.py` limited to
       the dependency-free `state` module and requiring `build_research_graph` to be imported
       directly from `ai.graph.build`.
    2. `ResearchState.revision_count` has no graph-level default (it mirrors
       `research_sessions.revision_count`'s DB default, set by whoever constructs the initial
       state) — an early test omitted it and got a `KeyError`, which was actually the test being
       unrealistic rather than a product bug, but worth documenting explicitly in `state.py`.
  Also corrected a real gap in the Phase 1 architecture diagram: it never actually wired the
  Summarizer agent into the graph at all. It now sits between Retriever and Fact Checker.
- Phase 8: Research Pipeline — real agents and real end-to-end execution, replacing Phase 7's stub
  passthroughs. `ai/tools/` (`BaseTool` ABC + DuckDuckGo/`ddgs`, Arxiv, Wikipedia — Wikipedia's REST
  API requires a descriptive `User-Agent` or it 403s), `ResearchState.research_findings` upgraded
  from `list[str]` to structured `ResearchFinding` dicts so the Citation agent can build real
  citations from source metadata instead of parsing prose. All 10 agents now do real work: Research
  fans out across every tool concurrently, Summarizer/FactChecker/Writer/Reviewer/Evaluation make
  real LLM calls, Citation is deterministic (no LLM) over `research_findings`. Built the REST
  surface the pipeline needs: `app/schemas|repositories|services` for `Project`/`ResearchSession`,
  `app/api/v1/projects.py` + `sessions.py` (`POST /projects/{id}/sessions` creates the session and
  enqueues `research.run_pipeline` by task name — the API process never imports `ai/graph`, keeping
  its import graph independent of the worker's). `app/workers/tasks.py` wraps
  `build_research_graph()` in a Celery task: streams `graph.astream(..., stream_mode="updates")`,
  persists an `AgentRun` + `Message` row per step and the final `Report`/`Citation` rows, and
  publishes each step over Redis pub/sub (`app/core/pubsub.py`) for `app/api/ws.py`
  (`/ws/sessions/{id}?token=`) to relay to the browser.
  No Redis available in this sandbox (Memurai's Windows Service installer fails here with an
  access-denied error, unlike Ollama which installs as a plain per-user process) — verified pub/sub
  live anyway via a shared in-process `fakeredis` server (confirmed `fakeredis.TcpFakeServer`,
  the real-socket mode, does *not* relay pub/sub across separate client connections; the in-process
  `FakeServer` shared between `FakeRedis(server=...)` instances does). Ran the actual exit
  criterion end-to-end against a real Postgres+pgvector instance and a real local Ollama
  (`llama3.2:1b`) + BGE (`bge-small-en-v1.5`) — register → login → create project → create session
  via the real REST endpoint → run the real worker task directly (bypassing only
  `celery_app.send_task`'s broker hop, since there's no broker here) → observed every pub/sub event
  in order → confirmed a persisted `Report` + `Citation` rows and one `AgentRun`/`Message` per graph
  step. Permanent regression test: `backend/tests/integration/test_research_pipeline.py`
  (opt-in, same gating as the other integration tests). 42 passed, 1 skipped across
  backend+ai/+integration run together; ruff/mypy(strict) clean.
  Real bugs caught by insisting on running the actual pipeline to completion, not just unit-testing
  routing predicates in isolation:
    1. **Infinite loop**: nothing ever incremented `revision_count`, so `routing.py`'s
       `revision_count < max_revision_loops` cap check was permanently true — an LLM that never
       says VERIFIED/APPROVED made both revision loops (fact_checker→research, reviewer→writer) run
       forever. Fixed by having `FactCheckerAgent`/`ReviewerAgent` bump `revision_count` themselves
       whenever their own verdict fails; `routing.py` only ever reads the cap. Added
       `test_revision_loops_terminate_at_the_cap_instead_of_looping_forever` as a permanent
       `asyncio.wait_for(..., timeout=10)`-guarded regression test.
    2. **Runaway local-model generation**: five of six LLM-calling agents (all but Writer) never
       set `max_tokens`, so nothing capped generation length. Against a real local Ollama model this
       wasn't hypothetical — one live pipeline run took over 30 minutes on a single fact-checker
       call before being killed, versus ~3-4 minutes once every agent got a sensible cap
       (planner 300, summarizer 600, fact-checker 150, reviewer 500, evaluation 20 tokens).
    3. **Cross-event-loop connection leak in tests**: Starlette's `TestClient` spins up its own
       background event loop per `with TestClient(app)` block, independent of pytest-asyncio's own
       loop scope; the shared `app.state.container.db_engine` (built once at import) leaked pooled
       asyncpg connections across those independently-scoped loops, crashing unrelated tests' own
       teardown at an arbitrary later point whenever Python's GC reaped the stale connection.
       Fixed by disposing the engine in `app/main.py`'s lifespan shutdown — good production hygiene
       (graceful connection teardown on SIGTERM) that also happens to fix the test isolation issue.
    4. Two Phase 4 integration-test assertions (`test_models_db.py`) assumed tables they didn't own
       started empty — true when written, false as soon as the `agents` seed table (Phase 7) and
       other tests' own persisted rows (this phase's pipeline test) are normal parts of a real
       database. Rewrote them to scope by this-test's-own ids/before-after counts instead of
       asserting global table emptiness.
- Phase 9: Vector Database — a real knowledge-base search pipeline, replacing the Retriever agent's
  Phase 7/8 stub (embedded the query, always returned empty context). `ai/chunking.py` (a small,
  dependency-free paragraph-aware splitter with overlap — not LangChain's splitters, which
  `docs/tech-stack.md` scopes to Phase 10's format-aware document loaders), `ai/vectorstore/`
  (`VectorStore` ABC + `RetrievedChunk`, mirroring `ai/tools/base.py`'s pattern: ai/ defines the
  interface and a `NullVectorStore` default, the backend constructs and injects the real
  implementation). `RetrieverAgent` now does a real similarity search and `ResearchState.retrieved_context`
  is `Annotated[..., operator.add]` like `research_findings` (the fact-checker revision loop
  re-enters Retriever too); `SummarizerAgent` now folds knowledge-base excerpts into its prompt
  alongside web/Arxiv/Wikipedia findings, so retrieval actually influences the final report instead
  of being wired up and ignored.
  Backend: `app/repositories/embedding.py` (the real `<=>` cosine-distance query via pgvector,
  project-scoped through a join on `documents`), `app/services/knowledge_base_service.py`
  (`ingest_text`/`search` — document *upload*, multipart files, PDF/DOCX parsing, and MinIO storage
  are Phase 10; `ingest_text` takes already-extracted plain text directly, which is exactly what
  Phase 10's loaders will hand it once they exist), `app/services/pg_vector_store.py` (the adapter
  binding `EmbeddingRepository` to `ai.vectorstore.base.VectorStore` for the graph, constructed
  fresh per pipeline run in `app/workers/tasks.py` — not a `Container` singleton, matching
  `AuthService`'s reasoning), and `GET /knowledge-base/search` (real REST endpoint; no ingestion
  endpoint yet, deliberately — see the service's docstring).
  No new migration needed — Phase 4 already created the `embeddings` table with pgvector's HNSW
  index. Verified live against a real Postgres+pgvector instance and the real default embedding
  model (BGE-large, 1024-dim — not the smaller/faster variant used elsewhere for speed, see the bug
  below): ingested three semantically distinct texts into a project, queried for a related topic,
  and confirmed pgvector actually ranks by relevance (the most on-topic chunk came back first,
  scores strictly descending) with correct project scoping (a same-topic chunk in a different
  project never appears) and correct 404-on-someone-else's-project behavior. Separately, extended
  `test_research_pipeline.py` (Phase 8) to index a real document before running the pipeline and
  confirmed the Retriever agent's real pgvector search — not just a stub — finds it inside an
  actual end-to-end run. 52 passed, 1 skipped across backend+ai/+integration run together;
  ruff/mypy(strict) clean.
  One real bug caught by that same pipeline test, immediately after wiring `PgVectorStore` in:
  `app/models/embedding.py`'s `embeddings.embedding` column is a **fixed** `vector(1024)` (BGE-large's
  native dimension, set at migration time) — it does not adapt to whatever `Settings.embedding_dimension`
  happens to be configured to at runtime. The test's worker had been reusing a smaller/faster BGE
  variant (384-dim) for speed the way Phase 7/8's tests do; the Retriever agent's first real query
  against the real 1024-dim column failed immediately with pgvector's own dimension-mismatch error
  — regardless of whether any rows were indexed, since the check happens on the query parameter's
  type, not the result set. Fixed by switching that test to the real default (bge-large,
  1024-dim); documented the underlying constraint (one embedding dimension per deployment, fixed by
  migration, not by `EMBEDDING_PROVIDER`) in `docs/architecture.md` § 7 for whoever configures a
  different provider later.
  Also flagged, not fixed (out of Phase 9's scope): `GET /knowledge-base/search` needs
  `container.embeddings` synchronously from the API process, which — with the default
  `EMBEDDING_PROVIDER=bge` — means the API image now needs `sentence-transformers`/`torch` too,
  contradicting `docker/backend/Dockerfile`'s "deliberately lean, no local-model deps" design from
  Phase 7. Noted in `app/api/deps.py`'s `get_knowledge_base_service` for Phase 13 (Deployment) to
  resolve — not a problem in this project's Docker-less dev/verification setup, since every process
  shares one Python environment with every dependency installed.
- Phase 10: Knowledge Base — every document source type uploads/imports, processes to `indexed`,
  and appears searchable in a real UI, replacing Phase 9's `ingest_text`-only, no-upload-endpoint
  state. `ai/loaders/` (`BaseLoader` ABC + `PdfLoader`/`DocxLoader`/`TextLoader`/`MarkdownLoader`/
  `CsvLoader`/`UrlLoader`/`YoutubeLoader`, mirroring `ai/tools/`'s registry pattern): pypdf,
  python-docx, markdown-it-py rendered to HTML then stripped with BeautifulSoup (added as a new
  dependency — hand-rolled regex HTML parsing, the pattern `ai/tools/wikipedia_search.py` used for a
  single known tag, doesn't generalize to arbitrary pages), `youtube-transcript-api`, and BeautifulSoup
  again for web pages. `app/core/object_storage.py` (a boto3 S3 client against MinIO, wrapped in
  `asyncio.to_thread`; a `Container` `cached_property` — an S3 client has no per-request state to
  isolate, unlike Phase 9's `VectorStore`). `KnowledgeBaseService` split into
  `upload_document`/`import_url` (router persists bytes/URL + a `pending` `Document` row
  synchronously) and `process_document` (a new `knowledge_base.process_document` Celery task fetches
  the content back, runs the matching loader, chunks, embeds, indexes — reusing Phase 9's
  `_chunk_and_index` unchanged). New endpoints: `POST /documents/upload`, `POST /documents/import-url`,
  `GET /documents/{id}`, `DELETE /documents/{id}`, `GET /projects/{id}/documents` (chunk counts per
  document, for the UI). Real frontend: `app/(dashboard)/knowledge-base/page.tsx` — project
  switcher/creation, upload + import-URL, a live document grid (polling while anything is
  pending/processing), and real semantic search — plus the `apiClient.upload()` multipart method and
  `use-projects`/`use-knowledge-base` TanStack Query hooks it's built on.
  MinIO has no Windows Service dependency (unlike Memurai, which failed to install in Phase 8) — its
  server ships as a single portable binary, run directly (`minio.exe server ./data`) for genuinely
  live object-storage verification. A portable, no-install Redis-for-Windows build (from
  `redis-windows/redis-windows`'s non-service release) was available too, so — unlike every earlier
  phase — this one got a **real** Redis broker and a **real** Celery worker process, not fakeredis or
  direct task-function calls: `POST /documents/upload` really enqueues onto a real queue, a real
  `celery worker` process really dequeues and runs it. Verified live end-to-end twice: (1) a backend
  integration test drove all 7 source types (a hand-built minimal PDF, a generated DOCX, plain text,
  CSV, Markdown, `https://example.com`, and a real YouTube video) through upload/import →
  `indexed` → a `/knowledge-base/search` hit ranking the right chunk first → delete → `404`; (2) a
  Playwright test drove the identical flow through the real browser UI against the real worker.
  ruff/mypy(strict) clean; 69 passed/2 skipped (backend+ai/+integration), 8 vitest unit tests, 2
  Playwright e2e specs, clean `next build`.
  Two real bugs, both found only because this phase finally had a real, persistent, multi-task
  worker process to test against (every earlier phase's verification used a fresh container/engine
  per test, which structurally could never trigger either):
    1. **Cross-event-loop connection reuse crash** — `app/workers/tasks.py`'s module-global
       `_container` (and its DB connection pool) is reused across every task a worker process ever
       runs, but each task's `asyncio.run(...)` creates and tears down its *own* event loop. A pooled
       asyncpg connection is bound to the loop that created it; the second task handed to a
       long-running worker got a connection from the first task's already-closed loop and crashed
       with `AttributeError: 'NoneType' object has no attribute 'send'` deep in asyncpg — this affects
       `research.run_pipeline` identically, not just the new document-processing task, and would hit
       any real production worker after its second task, guaranteed. Fixed by disposing
       `container.db_engine` in a `finally` block at the end of every task
       (`app/workers/tasks.py::_dispose_engine`), forcing a fresh connection (bound to whichever loop
       is live) on each new task. Confirmed fixed by running the same browser flow three times in a
       row against one worker process without a restart.
    2. **MinIO upload/download bucket mismatch** — an early version of the live document test
       configured the "worker" container's `minio_bucket_documents` independently of the real API
       process's container (which actually performs the upload); the two disagreed on bucket name,
       so the processing task's download 404'd (`NoSuchKey`) even though the upload had genuinely
       succeeded. Fixed by deriving the test's bucket name from the real API container's settings
       instead of hardcoding a second one.
  Also directly observed (not a bug, a confirmation of Phase 9's flagged item): the first
  `container.embeddings`-touching request in a freshly-started API process pays a one-time BGE
  model load (HuggingFace Hub checks + weight loading) before it can respond — a real, measured
  multi-second delay from the browser's perspective on the Knowledge Base page's very first
  interaction, not just a theoretical Phase 13 concern.
- Phase 11: Analytics — real (non-mock) session throughput, quality-gate outcomes, and per-agent
  token usage, replacing Phase 6's placeholder page. `ai/llm/base.py`'s `LLMResponse` (`content`,
  `prompt_tokens`, `completion_tokens`, `model`) replaces the bare `str` all three providers
  (`OpenAIProvider`/`AnthropicProvider`/`OllamaProvider`) used to return, each now extracting real
  per-call usage from the vendor's own response (`response.usage.prompt_tokens`/`completion_tokens`
  for OpenAI, `.input_tokens`/`.output_tokens` for Anthropic, `prompt_eval_count`/`eval_count` for
  Ollama) instead of estimating from text length. All six LLM-calling agents
  (planner/summarizer/fact_checker/writer/reviewer/evaluation) now read `response.content` and
  spread the usage onto their returned state dict (`BaseAgent._llm_usage`); `ai/graph/state.py`
  gained plain `prompt_tokens`/`completion_tokens`/`llm_model` fields so `app/workers/tasks.py`
  persists them straight into the existing `AgentRun.output_state` JSONB column — no new migration.
  `AnalyticsEventRepository` (`app/repositories/analytics_event.py`) now records 8 lifecycle events
  (`user.registered`, `project.created`, `session.created`/`.completed`/`.failed`,
  `document.uploaded`/`imported`/`indexed`/`failed`) into the `analytics_events` table Phase 4
  already created. `AnalyticsService` (`app/services/analytics_service.py`) computes
  `sessions_run`/`avg_completion_seconds`/`success_rate`/`sessions_over_time` directly from
  `research_sessions`, and a fact_checker/reviewer quality-gate **rejection rate** from
  `AgentRun.output_state`'s persisted verdict fields — reinterpreted from the original "agent
  failure rate" wireframe language (`docs/ui-wireframes.md` § 9) because Phase 8 never persists a
  per-node crash (a whole session just gets marked `failed`), so a literal crash-rate-by-agent chart
  isn't derivable from what's actually recorded; a quality-gate rejection rate is the closest real,
  honest signal. Three endpoints: `GET /analytics/overview|usage|activity` (`app/api/v1/analytics.py`).
  Real frontend: `app/(dashboard)/analytics/page.tsx` — KPI cards, a sessions-over-time line chart
  and a rejection-rate-by-agent bar chart (`recharts`, added as a new dependency — shadcn/ui's own
  chart components are built on it and no charting library existed yet), a token-usage-by-agent
  table, and a recent-activity feed — plus `hooks/use-analytics.ts`'s three TanStack Query hooks.
  Verified live end-to-end against a real Postgres+pgvector instance, real local Ollama
  (`llama3.2:1b`) + BGE (`bge-large-en-v1.5`), a real Redis broker, and a real persistent Celery
  worker (not fakeredis/direct task calls, for the first time for this particular task — see the
  bugs below): a permanent `backend/tests/integration/test_analytics.py` runs one full pipeline
  session through the real HTTP API and asserts the overview/usage/activity endpoints reflect that
  exact run; a permanent `frontend/tests/e2e/analytics.spec.ts` registers via the real browser, then
  — since there's no Workspace UI yet to start a session from the browser itself (Phase 8 only
  shipped the API/WebSocket half; `app/(dashboard)/workspace` is still Phase 6's placeholder) —
  drives one real session through the same REST endpoints a future Workspace page would call, polls
  it to completion (a real 6-agent run against a local CPU Ollama model takes ~4 minutes), and
  confirms the Analytics Dashboard renders that exact run's real numbers in a real headless-Chromium
  session. 70 passed/2 skipped (backend+ai/+integration, including two full live pipeline runs),
  8 vitest unit tests, 3 Playwright e2e specs, clean `next build`, ruff/mypy(strict) clean on both
  `backend/` and `ai/`.
  One real bug caught purely by live testing, not code review — mypy reported zero errors because
  `assert isinstance(reply, str)` in `ai/tests/test_live_ollama.py` had narrowed the checker's view
  of `reply` to `str` for every line after it, even though `reply` was actually the new
  `LLMResponse` and `reply.strip()` would have crashed at runtime the moment the test actually ran.
  A second, systemic bug, found the same way Phase 10's live-DB-session-test caught the DB-engine
  bug: `UUIDPrimaryKeyMixin`'s `default=uuid.uuid4` is a SQLAlchemy **column** default, only
  evaluated at flush time — a freshly constructed model's `.id` reads back as `None` before that.
  Four services (`AuthService.register`, `ProjectService.create_project`,
  `ResearchSessionService.create_session`, `KnowledgeBaseService.upload_document`/`import_url`) were
  each reading `model.id` to build their own analytics-event payload/`user_id`/`session_id` in the
  same breath as constructing the model — caught live when `test_analytics.py` got back only 3 of 4
  expected event types, then confirmed directly against Postgres: a `user_id: None` row and a
  literal `payload: {"project_id": "None"}` (the *string* `"None"`, from `str(None)`). Fixed in all
  four places by generating the UUID in Python first and passing `id=<uuid>` into the constructor,
  so the same local variable is valid for both the INSERT and the analytics event.
  A third bug — the most significant one this phase, and specific to standing up a real, persistent
  Celery worker and running more than one real pipeline session through it, which no earlier phase's
  verification had ever done — turned out to be the same root cause hitting three different
  `Container` attributes in turn. Phase 10 had already fixed it once for `container.db_engine`
  (a pooled asyncpg connection bound to the event loop that created it, crashing the *next* task's
  new loop). Getting a real Redis broker and a real Celery worker running for this phase's own
  Playwright verification exposed the identical defect in `container.redis` — `publish_event` is
  only ever called from `_run_pipeline_async`, which no earlier phase's real-Redis worker test
  (Phase 10's was `process_document_task`, which never calls it) had exercised twice in one process
  — crashing the second of two real pipeline runs with `RuntimeError: Event loop is closed` deep in
  redis-py. Fixing that and re-running the same two-runs-in-one-worker scenario immediately surfaced
  a *third* instance: `container.llm` wraps each vendor SDK's own async, httpx-based client, equally
  cached for the worker's lifetime, and crashed the same way mid-`planner`-node in httpcore instead
  of redis-py. All three are now released at the end of every task
  (`app/workers/tasks.py::_release_event_loop_bound_connections`, renamed from `_dispose_engine`):
  `db_engine.dispose()` and `redis.aclose()` as before (both types tolerate being reused afterward —
  they lazily reconnect on the next loop), plus dropping the `llm` `cached_property` outright (an SDK
  client has no such reconnect, but rebuilding one is free — the real connection opens lazily on
  first request regardless). `container.embeddings` is deliberately left alone: the default local
  BGE provider runs inference via `asyncio.to_thread` around a synchronous, in-process model with no
  persistent async client to go stale, and resetting it the same way would force a multi-second model
  reload on every task, including every document-processing task's hot path, for zero benefit.
  Confirmed fixed by running two real pipeline sessions back to back against one worker process —
  once directly (a throwaway smoke-test session), then again via the real `analytics.spec.ts` run —
  without restarting the worker in between.
- Phase 12: Testing — the integration/e2e layer and CI enforcement promised in
  `docs/milestones.md`'s sequencing notes, plus (with explicit sign-off — see that discussion) the
  real Workspace/Reports UI Phase 12's own exit criterion turned out to require: a genuine
  Playwright e2e for "the core research flow" needs somewhere in the browser to actually start and
  watch a session, and `app/(dashboard)/workspace`/`reports` were still Phase 6 placeholders.
  `GET /projects/{id}/sessions` (`app/api/v1/sessions.py`) — the one missing route; the
  service/repository method existed since Phase 8. `app/(dashboard)/workspace/page.tsx`: project
  picker, a query form (`POST /projects/{id}/sessions`), a live agent-progress checklist and
  streaming trace driven by a new `hooks/use-session-events.ts` (a thin `WebSocket` wrapper around
  `/ws/sessions/{id}`), and a session history list. `app/(dashboard)/reports/page.tsx`: a session
  list plus the selected session's report rendered as real markdown (`react-markdown` +
  `@tailwindcss/typography`, both new dependencies — shadcn/ui-adjacent projects standardize on the
  same combination). Deliberately scoped down from `docs/ui-wireframes.md` § 5's full 3-pane design
  (animated node transitions, a dedicated citation/source panel, inline follow-up refinement,
  multi-format export) — those remain aspirational/future work; what's built is real and
  functionally complete for the "submit → watch → read" flow, not a mockup. One real, load-bearing
  UX honesty constraint drove the progress checklist's design: `app/api/ws.py` only ever emits a
  node_update *after* a node finishes, never on start, so there is no real "currently running"
  signal to render — the checklist shows "done" (completed at least once — a revision loop can
  re-complete a node) and flags the most recent completion as "latest" rather than faking a
  live/active state the backend doesn't actually report.
  Frontend component tests (`@testing-library/react`, installed since Phase 6 but never actually
  used until now): `AuthGuard` (redirect-when-unauthenticated/expired-token logic), `Sidebar`
  (nav rendering, active-route highlighting including nested-route prefix matching), and the new
  Workspace page's `AgentProgressList` (done/latest/revision-loop-reentry rendering logic) — 15
  tests across 3 files, zero live infra. Backend unit tests: `backend/tests/test_security.py`, 12
  tests covering `app/core/security.py`'s JWT/bcrypt/refresh-token logic in isolation (round-trip,
  tampered signature, wrong-key, expired, wrong-claim-type, bcrypt's 72-byte truncation edge case) —
  previously only exercised indirectly through `test_auth.py`'s live integration coverage.
  `frontend/tests/e2e/research-flow.spec.ts`: register → submit a query through the real Workspace
  UI → watch real node-by-node progress over the real WebSocket → real completion → real rendered
  report on the Reports page — no API shortcuts, unlike `analytics.spec.ts` (which had no UI to
  drive before this phase). `.github/workflows/ci.yml`: two jobs (backend: ruff, mypy --strict,
  pytest; frontend: eslint, tsc, vitest, next build) running the same live-infra-free half of the
  suite `make test-backend`/`make test-frontend` already ran locally — deliberately *not*
  provisioning Postgres/Redis/MinIO/Ollama service containers for the opt-in integration tests or
  the four Playwright specs, the same two-tier split (fast/offline vs. opt-in/live-infra) the suite
  has used since Phase 8, now made explicit in one place. Verified live: 82 passed/2 skipped
  (backend+ai/+integration, up from 70 — the 12 new security tests plus the sessions-list endpoint
  exercised for the first time), 19 vitest tests (up from 8), all 4 Playwright specs green, clean
  `next build`, ruff/mypy(strict) clean on both `backend/` and `ai/`. No GitHub remote exists yet for
  this repo (0 commits so far — see `git log`), so `ci.yml` is verified by YAML-parsing it and by
  having already run its exact command sequence manually against the same dependency set, not by an
  actual triggered Actions run.
  Two real bugs, both caught only by actually running things, not by review:
    1. **Testing Library's auto-cleanup silently never ran.** `vitest.config.ts` doesn't set
       `test.globals: true`, and `@testing-library/react`'s automatic `afterEach(cleanup)`
       registration only self-activates when it detects `afterEach` already on `globalThis` — so
       every `render()` call was leaking its DOM into the next test in the same file. Invisible
       until this phase because no earlier test file had ever called `render()` more than once;
       the very first multi-`render()` test file (`sidebar.test.tsx`) immediately hit
       `getByRole` matching duplicate leftover nav links from an unmounted previous render. Fixed
       by explicitly registering `afterEach(() => cleanup())` in `vitest.setup.ts`, the documented
       fallback for exactly this configuration.
    2. **A transient "socket hang up"/ECONNRESET polling a long-running session**, real but
       environmental rather than a product defect: `analytics.spec.ts`'s poll loop occasionally lost
       a single `GET /sessions/{id}` mid-run while the sibling Celery worker process was under
       sustained real CPU load from local Ollama/BGE inference — reproduced even with the test run
       in complete isolation (no other spec or task competing for the worker), and the pipeline
       itself always completed successfully regardless, confirming the run itself was never at
       fault. Hardened the poll loop to swallow one failed attempt and retry on the next tick rather
       than fail the whole multi-minute test over a single dropped connection — ordinary resilience
       for a long-lived polling loop over a real network connection, not a workaround for a logic
       bug.
  Also directly observed (not itself a bug): running all 4 Playwright specs together against a
  single solo-pool Celery worker starves whichever spec's task gets queued behind another spec's
  still-in-flight ~2-4 minute pipeline run, producing failures that look like product bugs (a 60s
  "first live update" budget expiring because the task hadn't even started yet) but are purely
  queueing artifacts of one worker process serving multiple heavy tests back to back. Each spec is
  verified individually for this reason; this is a test-execution/infra constraint of a single local
  dev machine, not something `research-flow.spec.ts`/`analytics.spec.ts` need to work around
  themselves.
- Phase 13: Deployment — completed the `docker-compose.yml`/Dockerfiles/Nginx/Prometheus/Grafana
  skeleton Phase 2 sketched (deliberately "not yet all buildable" at the time) into something meant
  to actually work end to end. **No Docker Engine is available in the authoring environment at
  all** (unlike every prior phase's infra gap — Redis-as-a-Windows-service, no OpenAI/Anthropic
  credentials — where a real substitute was found; there is no substitute for "does the image
  build"), so `docker compose up` itself was never run — flagged explicitly, with your sign-off on
  proceeding this way, rather than silently claimed as verified. Everything else was verified as
  rigorously as the constraint allows: every YAML/JSON config parses (`docker-compose.yml`,
  `docker-compose.prod.yml`, `prometheus.yml`, both Grafana provisioning files, the new dashboard
  JSON), every `${VAR}` referenced across both compose files has a matching `.env.example` entry,
  and — critically — the backend/worker images' actual dependency-install step
  (`uv pip install -e .`/`-e ".[local]"`) was reproduced by hand outside Docker against the exact
  file layout the Dockerfiles construct, which is what caught the two real bugs below.
  Added: `.dockerignore` (repo root + `frontend/`), a `HEALTHCHECK` for `backend` (`curl
  /health`) and `worker` (`celery inspect ping`) with `frontend`/`nginx` upgraded to
  `depends_on: condition: service_healthy` throughout; two new sidecar exporters
  (`danihodovic/celery-exporter`, `quay.io/prometheuscommunity/postgres-exporter` — image names,
  ports, and env var formats confirmed against each project's own docs, not guessed) wired into
  `prometheus.yml`'s scrape config (which already anticipated them, unfulfilled, since Phase 2); a
  real Grafana dashboard (`docker/grafana/provisioning/dashboards/json/platform-overview.json`) —
  HTTP request rate/p95 latency/error rate from `prometheus-fastapi-instrumentator`'s own default
  metric names, Celery task throughput/runtime/queue depth, Postgres connections/transaction rate —
  replacing a stale comment that (incorrectly, in hindsight) attributed this to Phase 11, which was
  always the in-app product-analytics page, not infra/ops observability; `docker/nginx/nginx.prod.conf.example`,
  a complete TLS-ready server block deliberately kept separate from the working default (a fake
  self-signed cert would be misleading, and a real one needs a real domain + ACME client this repo
  can't run for you); and `docs/deployment.md`, the Phase 13 deployment guide (quick start,
  service map, running fully local via the `local-ai` profile, the prod override, enabling HTTPS,
  common operations, troubleshooting) — with an explicit verification-limitation note up top.
  Three real bugs, none of which any earlier phase's tooling could have caught (nothing had ever
  tried to build these images):
    1. **`alembic.ini`/`alembic/` were never copied into the backend/worker images** — `make
       migrate` (`docker compose exec backend alembic upgrade head`) would have failed immediately
       on a fresh checkout with no schema at all. Added both to `docker/backend/Dockerfile` (the
       migration target); left out of the worker image, which never runs migrations itself.
    2. **Hatchling's editable install hard-fails without `README.md`** —
       `backend/pyproject.toml`'s `readme = "../README.md"` resolves relative to
       `/srv/backend/pyproject.toml`, i.e. `/srv/README.md`, which neither Dockerfile ever copied.
       Reproduced directly (outside Docker): a bare `uv pip install -e .` against the exact
       `/srv/backend` layout the Dockerfiles construct fails with `OSError: Readme file does not
       exist: ../README.md` from deep inside `hatchling.metadata.core`; re-running the identical
       command with the file present succeeds. Fixed by adding `COPY README.md /srv/README.md` to
       both Dockerfiles — and, since the new root `.dockerignore`'s blanket `*.md` rule would have
       excluded it right back out of the build context, an explicit `!README.md` negation.
    3. **`frontend/public/` doesn't exist in this repo** (no static assets were ever needed —
       Next.js makes the folder optional) — the `runner` stage's `COPY --from=builder /app/public
       ./public` would fail outright with a missing-source-path error. Added
       `frontend/public/.gitkeep` so the directory exists to be copied; confirmed `npm run build`
       is unaffected.
  One more real, subtler bug, caught by reasoning through Next.js's build model rather than by a
  direct repro: `NEXT_PUBLIC_API_BASE_URL`/`NEXT_PUBLIC_WS_BASE_URL` are inlined into the static
  client bundle at `next build` time, not read from the container's environment at runtime, for
  the production (`runner`) stage — unlike the `dev` stage's `npm run dev`, which does read them
  live. `docker/frontend/Dockerfile`'s `builder` stage had no `ARG`/`ENV` declarations for either,
  so a prod build would have silently baked in the code's hardcoded `localhost:8000` fallbacks
  regardless of what `.env` said. Fixed by declaring both as build `ARG`s and passing them through
  `docker-compose.prod.yml`'s new `frontend.build.args` (with prod-appropriate defaults routed
  through Nginx rather than a direct backend port) — documented explicitly in
  `docs/deployment.md` § 5, since changing `.env` after the image is already built now has no
  effect without a rebuild, a real (if well-precedented) footgun worth calling out rather than
  leaving implicit.
  Also hardened, not a bug: `docker-compose.prod.yml` now drops `backend`'s host port too (only
  `nginx` and `minio`'s console stay reachable directly), matching the existing
  `postgres`/`redis` treatment.
- Phase 14: Documentation — reconciled the whole `docs/` set against the real, current code rather
  than the original Phase 1 plan, and wrote the two documents that had only ever existed as
  forward references. The exit criterion ("a new contributor can go from `git clone` to a working
  local instance using only the docs") turned out to demand a real audit, not a light pass:
  `README.md` still read "Phase 1 (Planning) complete. No application code exists yet" — accurate
  in Phase 1, false for the previous twelve phases — and several sections of `docs/api-design.md`
  described endpoints/conventions (cursor pagination, an `Idempotency-Key` header, a
  session-creation-specific rate limit, a full `/reports`/`/agents` surface) that were sketched in
  the original plan but never actually built, with no annotation saying so.
  Rewrote `README.md` (accurate status, a real feature list, a `docs/` table including the two new
  documents below) and `CONTRIBUTING.md` (pointed at the real `docs/installation.md` instead of "full
  instructions land [here] eventually"; dropped a dangling reference to a `CLAUDE.md` that was never
  actually part of this repository). Corrected `docs/api-design.md`'s conventions section
  (pagination/filtering: not built, described as intended-future rather than present; rate
  limiting: accurately scoped to the two routes that actually have it,
  `POST /auth/register`/`POST /auth/login`, not a fictional session-creation limit; idempotency:
  marked not implemented, with the real consequence — a dropped connection can enqueue a duplicate
  pipeline run today — stated plainly) and its resource-map diagram (now marks unbuilt routes with
  a dashed style instead of drawing them identically to real ones), and `docs/architecture.md` § 8
  (the `beat` service has no `beat_schedule` at all — an earlier revision's "e.g. analytics
  rollups" example described a feature that doesn't exist; Analytics computes everything live,
  per request). Added `docs/installation.md` (local dev, no Docker required — both a
  Docker-for-just-the-data-layer path and the fully-native path this project's own authoring
  environment actually used throughout every phase: `pgserver` for Postgres+pgvector, portable
  Redis/MinIO binaries) and `docs/roadmap.md` (a plain list of what's real vs. genuinely planned,
  split from things that are purely speculative).
  Two real, concrete bugs found by actually trying to follow the new installation guide rather
  than just writing it from memory:
    1. **`make install` couldn't run the default configuration.** `Makefile`'s `install-backend`
       ran `uv pip install -e "./backend[dev]"` — no `local` extra — but
       `EMBEDDING_PROVIDER=bge` is the default, and local (non-Docker) development runs the Celery
       worker directly rather than through `docker/worker/Dockerfile`'s own separate `[local]`
       install. Following the guide's own § 6 with only `[dev]` installed would have crashed the
       first time the worker imported `sentence_transformers`. Fixed by adding `local` to
       `install-backend`'s extras.
    2. **`make migrate`/`make seed` don't work without a running `backend` Docker container** —
       both run `docker compose exec backend ...`, which has nothing to exec into in either of
       `docs/installation.md`'s two infrastructure options (the backend always runs natively
       there). Fixed by documenting the direct commands (`alembic upgrade head`,
       `python -m app.scripts.seed`, run from `backend/`) instead.
  ruff/mypy(strict) unaffected (no application code touched this phase) — reconfirmed clean as a
  quick regression check. No live-infra verification needed for a docs-only phase; instead, every
  internal markdown link across the changed files was checked to resolve to a real path, and every
  code fence checked for balance.
- Phase 15: GitHub polishing — the final phase: making the repository front page read as a
  finished, credible open-source project, plus the real git history this repo never had. The
  project had been built and verified across 14 phases entirely inside a single uncommitted working
  tree (0 commits, per `git log`, as flagged as far back as Phase 12's CI notes) — this phase adds
  `run.ps1`/`stop.ps1` (a one-command native Windows dev stack: Postgres via `pgserver`, Redis,
  MinIO, backend, Celery worker, and frontend, each in its own window, with a health-check poll and
  auto-opened browser) and `scripts/start_postgres.py`/`stop_postgres.py`, then reconstructs 15
  commits — one per phase — each scoped to that phase's own files and messaged from this
  changelog's own account of what shipped, landing with today's real timestamp rather than
  fabricated historical dates. `.github/ISSUE_TEMPLATE/` (bug report, feature request) and
  `.github/PULL_REQUEST_TEMPLATE.md`; `README.md` gained a banner, a real CI/license/coverage badge
  row, and a screenshots section wired to `assets/screenshots/`; `assets/banner.svg` and
  `assets/screenshots/README.md` (the exact expected filenames, populated by hand from the running
  app rather than fabricated). Tagged as `v1.0.0` — the first release.
  Two real bugs, caught the same way every other phase's bugs were — by actually running things,
  not by reading them:
    1. **`run.ps1`'s own development surfaced four PowerShell/Windows environment bugs** before it
       was reliable enough to ship: a `-ArgumentList @(...)` array literal silently splits a
       multi-line command string built with a trailing `+` into extra array elements instead of
       concatenating it, desyncing everything parsed afterward; Windows PowerShell 5.1 reads
       UTF-8-without-BOM `.ps1` files via the system ANSI codepage, corrupting em-dashes and other
       multi-byte characters (fixed by keeping both scripts pure ASCII); a force-killed Postgres
       needs full crash recovery (WAL replay, a 30+ second fsync, plus Windows Defender routinely
       holding a fresh log file locked for 30 seconds) that blows past `pgserver`'s own hardcoded
       10-second start timeout, fixed by a real graceful `pg_ctl -m fast -w stop` in
       `stop_postgres.py`, plus killing Postgres's Windows worker sub-processes
       (`--forkaux`/`--forkbgworker`/etc.) as a full process tree rather than just the main
       postmaster PID, which otherwise survive as orphans holding the data directory lock; and
       `Invoke-WebRequest` against `localhost` intermittently failed where the identical request
       against `127.0.0.1` always succeeded, fixed by using `127.0.0.1` explicitly in both
       health-check loops.
    2. **`fakeredis` — used by `tests/integration/test_analytics.py` and
       `test_research_pipeline.py` since Phase 8 — was never declared in `backend/pyproject.toml`'s
       `dev` extra**, caught only now, running a coverage pass against a freshly-`uv`-synced
       virtualenv rather than the long-lived one every earlier phase's verification happened to
       reuse: both files failed to even import (`ModuleNotFoundError`), which would have made
       `pytest`'s collection step itself fail on any clean clone. Added `fakeredis>=2.31,<3.0` to
       `dev`; confirmed fixed by a clean `uv pip install -e ".[dev,local]"` followed by a full
       `pytest --cov` run: 71 passed / 13 skipped (the skips are the integration tests whose own
       `skipif` guards correctly detect no live Postgres/Redis/MinIO/Ollama is running in this
       pass), 65% backend line coverage — the honest offline-unit-test number, not inflated by the
       live-infra-only paths the opt-in integration/e2e suites cover instead.
