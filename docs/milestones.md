# Milestones

One milestone per build phase. Each phase has explicit **exit criteria** — the phase is not
"done" until its own code/config compiles, runs, or passes CI as stated. No phase starts until
the previous phase's exit criteria are met and you've approved moving on.

| Phase | Name | Deliverables | Exit criteria |
|---|---|---|---|
| 1 | Project planning | This `docs/` set: architecture, tech stack, DB schema, API design, wireframes, folder structure, milestones, initial README | You approve this document set |
| 2 | Repository initialization | `git init`, `.gitignore`, `.env.example`, `docker-compose.yml` skeleton (services defined, not yet all buildable), base `Dockerfile`s, dependency manifests (`package.json`, `pyproject.toml`) with pinned core deps | `docker compose config` validates; `npm install` and `poetry install`/`pip install` succeed with no errors |
| 3 | Backend | FastAPI app skeleton: `core/config.py`, DI container, health check, versioned router mount, middleware stack, structured logging | `uvicorn app.main:app` boots; `GET /health` returns 200; OpenAPI docs render at `/api/docs` |
| 4 | Database | SQLAlchemy models for every table in [database-schema.md](database-schema.md), Alembic configured, first migration | `alembic upgrade head` runs clean against a fresh Postgres container; models import without circular deps |
| 5 | Authentication | JWT issuance/refresh, password hashing, OAuth (Google/GitHub) flow, auth middleware, protected-route dependency | Register → login → access a protected endpoint → refresh → logout all work via `curl`/pytest against a running instance |
| 6 | Frontend | Next.js app shell: routing, sidebar/topbar layout, auth pages, TanStack Query provider, API client, dark mode | `npm run build` succeeds; login page hits the real backend auth endpoints end-to-end |
| 7 | AI Agent Framework | `ai/` package: `BaseAgent` protocol, `LLMProvider`/`EmbeddingProvider` interfaces + OpenAI/Anthropic/Ollama/BGE implementations, LangGraph `StateGraph` wired with stub agent nodes | A no-op graph run (`graph.invoke(state)`) executes start-to-finish through all 10 stub nodes with at least one provider live |
| 8 | Research Pipeline | Real agent implementations (Planner → ... → Memory), Celery task wrapping the graph, WebSocket relay of node events | Submitting a query via API produces a real streamed multi-agent run and a persisted report row |
| 9 | Vector Database | pgvector extension + `embeddings` table, `EmbeddingProvider` wired to real chunking, similarity search endpoint | Uploading a doc and querying `/knowledge-base/search` returns relevant chunks ranked by cosine similarity |
| 10 | Knowledge Base | Document loaders (PDF/DOCX/TXT/CSV/MD/URL/YouTube), upload/import endpoints + processing status, KB browser UI | Every listed source type uploads/imports, processes to `indexed` status, and appears searchable in the UI |
| 11 | Analytics | `analytics_events` emission across key actions, aggregation endpoints, Analytics Dashboard UI with charts | Dashboard renders real (non-mock) session/usage data from at least one full pipeline run |
| 12 | Testing | pytest unit+integration suites (backend, ai/), frontend component tests, Playwright e2e for the core research flow | `make test` (or equivalent CI job) is green across all four suites |
| 13 | Deployment | Full `docker-compose.yml` (all services), Nginx config, Prometheus/Grafana provisioning, prod compose override, deployment guide | `docker compose up` from a clean checkout brings up the entire stack and the core research flow works end-to-end in containers |
| 14 | Documentation | Complete `docs/`: installation, architecture (finalized against real code), API docs, deployment guide, contributing guide, roadmap | A new contributor can go from `git clone` to a working local instance using only the docs |
| 15 | GitHub polishing | Issue/PR templates, badges (CI, license, coverage), first tagged release, demo GIF/screenshots, populated `assets/` | Repo front page (README) reads as a finished, credible open-source SaaS project |

## Definition of "compiles successfully" per phase

Since the instruction is that every phase must compile before the next starts, each backend-touching
phase (3–13) is only marked done once:

1. The relevant service builds in Docker (`docker compose build <service>`), and
2. Its own test suite (once Phase 12 exists) or a smoke check (before Phase 12) passes, and
3. No phase leaves a half-wired stub silently swallowing errors — stub implementations (e.g. the
   Phase 7 no-op agent nodes) are explicit `NotImplementedError`-free placeholders that do
   something real and observable (log + pass state through), not fake success paths.

## Sequencing notes

- Phase 5 (Auth) is deliberately before Phase 6 (Frontend) so the frontend is built against a real
  auth API from day one instead of being retrofitted later.
- Phase 7 (Agent Framework) before Phase 8 (Research Pipeline) separates "the graph and provider
  interfaces exist and run" from "the agents are actually good" — this keeps Phase 7 reviewable on
  its own instead of bundled into a much larger Phase 8.
- Phase 9 (Vector DB) before Phase 10 (Knowledge Base) because the KB UI/import endpoints need
  somewhere real to write embeddings to before they're built.
- Testing (12) is a dedicated phase, but in practice each earlier phase adds its own unit tests as
  it goes (per the "no half-finished implementations" ground rule) — Phase 12 is where the
  integration/e2e layer and CI enforcement get added on top of what already exists.
