# Installation (Local Development)

Setting up DeepResearch AI for local development — running the app natively (hot reload, your own
editor/debugger, fast test iteration) rather than the containerized deployment covered in
[deployment.md](deployment.md). If you just want to run the product, not modify it,
`docker compose up` per that guide is less setup.

## 1. Prerequisites

- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (`pip install uv`) — the backend's
  LangGraph/LangChain dependency tree resolves in seconds with `uv`; plain `pip`'s resolver was
  observed taking 3+ minutes (and once appearing to hang) on the same graph.
- **Node.js 20+** and npm.
- **Git.**
- **`make`** (optional) — every command below is also given in its raw, non-`make` form, since
  `make` isn't available by default on every platform (notably plain Windows/Git Bash, which this
  project's own authoring environment was) and installing one just to follow this guide is
  unnecessary friction.
- Something to run Postgres+pgvector/Redis/MinIO — either Docker, or native installs (§ 3 covers
  both).

## 2. Clone and configure

```bash
git clone <this-repo> && cd deep-research-ai
cp .env.example .env
```

Edit `.env`: set a real `SECRET_KEY` (`openssl rand -hex 32`), and update `DATABASE_URL`/
`REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`/`MINIO_ENDPOINT` to point at `localhost`
instead of the Docker service names (`postgres`, `redis`, `minio`) the defaults assume —
`backend/app/core/config.py`'s own Python-level defaults already use `localhost`, so if you'd
rather not edit `.env` for this, unset those four variables (or just don't source `.env` at all)
and rely on the code's defaults instead; either approach works, and the second one is what every
phase of this project's own live verification actually used.

Pick an LLM provider (`AI_PROVIDER`): a real `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, or install
[Ollama](https://ollama.com) and run it locally with no key needed — `ollama pull llama3.2:1b`
(a small, fast model; this project's own live verification throughout every phase used exactly
this one) and set `AI_PROVIDER=ollama`, `OLLAMA_MODEL=llama3.2:1b`. Leave
`EMBEDDING_PROVIDER=bge` (the default, fully local, no key) unless you'd rather use
`OPENAI_API_KEY` for embeddings too.

## 3. Install dependencies

```bash
make install
```

Equivalent to:

```bash
uv pip install -e "./backend[dev,local]"   # backend + ai/ — the `local` extra pulls in
                                             # sentence-transformers/torch for BGE embeddings
cd frontend && npm install
```

## 4. Infrastructure: Postgres+pgvector, Redis, MinIO

### Option A — Docker for just the data layer (least setup)

```bash
docker compose up -d postgres redis minio
```

Bind-mounts/hot-reload aren't relevant to these three services, so running them in containers
while the backend/frontend run natively on your host is a normal, low-friction split — you get a
real pgvector-enabled Postgres without installing it natively.

### Option B — Fully native (no Docker at all)

What this project's own development actually used throughout every phase, since the authoring
environment had no Docker available:

- **Postgres + pgvector**: either a native Postgres 16 install with the
  [pgvector](https://github.com/pgvector/pgvector) extension built/installed, or the
  [`pgserver`](https://pypi.org/project/pgserver/) PyPI package (`pip install pgserver`) — a
  real, disposable Postgres+pgvector binary distribution with no system install at all, genuinely
  used for every phase's live verification in this project, not just a testing convenience:

  ```python
  import pgserver
  srv = pgserver.get_server("./pgdata", cleanup_mode=None)  # persists across restarts
  print(srv.get_uri())  # postgresql://postgres:@127.0.0.1:<port>/postgres
  srv.psql("CREATE EXTENSION IF NOT EXISTS vector;")
  ```

  Point `DATABASE_URL` at the printed URI (swap `postgresql://` for `postgresql+asyncpg://`).

- **Redis**: a native install (`apt install redis-server`, `brew install redis`) on Linux/macOS.
  On Windows (no official Redis build), a portable, non-service binary release works well:
  [`redis-windows/redis-windows`](https://github.com/redis-windows/redis-windows)'s releases —
  download the build **without** `-with-Service` in its name, unzip, and run
  `redis-server.exe --port 6379` directly; no installer, no admin rights.
- **MinIO**: [download the single `minio` binary](https://min.io/docs/minio/linux/index.html) for
  your platform and run `minio server ./miniodata` directly — genuinely a single portable
  executable, no install step, on every platform this project ran it on.

## 5. Migrations and seed data

`make migrate`/`make seed` run against the `backend` *Docker* container (`docker compose exec
backend ...`) — not relevant here, since the backend runs natively in this guide, both with
Option A and Option B above. Run them directly instead:

```bash
cd backend
alembic upgrade head
python -m app.scripts.seed   # populates the `agents` reference table — required before any
                              # research session can run; a session against an unseeded
                              # database fails with a clear error rather than a raw
                              # foreign-key violation
```

## 6. Run the app

**Windows shortcut:** once steps 1-5 above have been done at least once (dependencies installed,
`.env` configured, migrations applied), `.\run.ps1` from the repo root starts everything —
Postgres (via `pgserver`), Redis, MinIO, the backend, the Celery worker, and the frontend, each in
its own window — waits for the backend health check, and opens the browser automatically.
`.\stop.ps1` tears it all down again, gracefully (a real `pg_ctl stop`, not a force-kill, to avoid
Postgres crash-recovery on the next start). Skip straight to
[step 7](#7-verify-it-works) after running it. Otherwise, four processes, each in its own terminal:

```bash
cd backend && uvicorn app.main:app --reload                                    # API :8000
cd backend && celery -A app.workers.celery_app worker --pool=solo --loglevel=info  # worker
                                     # --pool=solo on Windows (the default prefork pool
                                     # isn't well-supported there); omit it elsewhere
cd frontend && npm run dev                                                     # :3000
```

(Celery Beat exists in the topology but has no scheduled tasks defined yet — see
[architecture.md § 8](architecture.md#8-deployment-topology-docker-compose-services) — so there's
nothing to run locally for it.)

## 7. Verify it works

- `curl http://localhost:8000/health` → `{"status": "ok", ...}`
- `http://localhost:8000/api/docs` → interactive OpenAPI docs
- `http://localhost:3000` → register an account, create a project, submit a query on the
  Workspace page, and watch the real agent pipeline run live. A CPU-only local Ollama model takes
  a few minutes end to end — this project's own live verification consistently saw ~2–4 minutes
  for a full 6-agent LLM run.

## 8. Running the tests

```bash
make lint            # ruff (backend+ai) + eslint (frontend)
make test-backend     # pytest — backend/tests + ai/tests
make test-frontend    # vitest — frontend component/unit tests
make test-e2e         # Playwright — requires the full stack (§ 6) actually running
```

Without `make`:

```bash
cd backend && ruff check . ../ai && mypy app && mypy ../ai   # lint + strict type-check
cd backend && pytest                                          # test-backend
cd frontend && npm test                                       # test-frontend
cd frontend && npx playwright test                            # test-e2e
```

Most of `test-backend` runs with no live infrastructure at all — integration tests that need a
real Postgres (and, for a few, a reachable Ollama or MinIO) are gated behind
`RUN_INTEGRATION_TESTS=1` and self-skip otherwise (see any file under
`backend/tests/integration/`'s own `pytestmark`). Set it plus `DATABASE_URL` pointed at a
disposable database to run them for real:

```bash
RUN_INTEGRATION_TESTS=1 DATABASE_URL=<your test db url> make test-backend
```

Playwright's e2e specs each need the entire stack — backend, a real Celery worker, Redis, MinIO,
and (for the specs that run a real pipeline) Ollama — up and reachable at their default local
ports. Run specs needing a real multi-minute LLM pipeline (`analytics.spec.ts`,
`research-flow.spec.ts`) one at a time rather than all together: a single local Celery worker
processes one task at a time, so running them concurrently just queues one behind the other and
can trip a test's own timeout waiting on a task that hasn't started yet — not a product bug, see
`CHANGELOG.md`'s Phase 12 entry for the concrete failure this produces.
