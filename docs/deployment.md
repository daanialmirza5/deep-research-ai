# Deployment Guide

Deploying DeepResearch AI with Docker Compose — the full stack (Postgres+pgvector, Redis, MinIO,
the FastAPI backend, a Celery worker, the Next.js frontend, Nginx, and Prometheus/Grafana) running
as containers, either for local evaluation or as a starting point for a real deployment.

> **Verification note**: this guide and the Compose/Dockerfile configuration it describes were
> written and reviewed carefully (cross-checked line by line against the actual dependency
> manifests, `Settings` fields, and Makefile targets), but the authoring environment had no Docker
> installed, so `docker compose up` itself was never run there. Every other phase of this project
> was verified against a real, live instance of whatever it built; this phase is the one exception,
> flagged explicitly rather than silently glossed over. If something here doesn't work as described,
> please open an issue.

## 1. Prerequisites

- Docker Engine 24+ and Docker Compose v2 (`docker compose version` should print `v2.x`)
- ~10 GB free disk (the worker image includes `torch`/`sentence-transformers` for local BGE
  embeddings; Postgres/MinIO/Prometheus/Grafana volumes add up over time)
- Ports `80`, `3000`, `3001`, `5432`, `6379`, `8000`, `9000`, `9001`, `9090` free on the host (all
  overridable — see `.env.example`'s `PORTS` section)

## 2. Quick start

```bash
git clone <this-repo> && cd deep-research-ai
cp .env.example .env
```

Edit `.env`:

- Set real values for `SECRET_KEY` (`openssl rand -hex 32`), `POSTGRES_PASSWORD`,
  `MINIO_ROOT_PASSWORD`, `GRAFANA_ADMIN_PASSWORD` — the `.env.example` placeholders are not
  meant to be used as-is even for local evaluation.
- Pick an LLM provider (`AI_PROVIDER=openai|anthropic|ollama`) and set the matching API key, or use
  Ollama fully locally (see § 4).
- Leave `EMBEDDING_PROVIDER=bge` (the default) unless you have an `OPENAI_API_KEY` and prefer not
  to run a local embedding model — see `docs/architecture.md` § 7 for the tradeoff (BGE needs the
  worker image's `torch`/`sentence-transformers` extra; OpenAI embeddings don't, but cost money and
  need network access per call).

Bring up the stack, then apply migrations and seed the agent registry (deliberately separate,
explicit steps — see `Makefile` — not run automatically on container start, so a bad rollout can't
silently re-run migrations against a database it shouldn't touch):

```bash
docker compose up -d --build
make migrate
make seed
```

`docker compose ps` should show every service `healthy` within a minute or two (the backend/worker
images' first build is the slow step — the worker's `torch`/`sentence-transformers` install in
particular; subsequent builds are cached). Then:

- Frontend: http://localhost (via Nginx) or http://localhost:3000 directly
- API docs: http://localhost:8000/api/docs
- MinIO console: http://localhost:9001 (`MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD`)
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (`GRAFANA_ADMIN_USER`/`GRAFANA_ADMIN_PASSWORD`; the
  "DeepResearch AI — Platform Overview" dashboard is provisioned automatically)

Register an account, create a project, and submit a query on the Workspace page — the same "core
research flow" verified live against local processes in Phases 8–12, now running in containers.

## 3. Service map

| Service | Purpose | Host port (default) |
|---|---|---|
| `nginx` | single entry point, routes `/` to frontend, `/api/`+`/ws/` to backend | 80 |
| `frontend` | Next.js app | 3000 |
| `backend` | FastAPI (REST + WebSocket), enqueues Celery tasks | 8000 |
| `worker` | Celery worker — runs the LangGraph pipeline + document processing | — |
| `beat` | Celery beat — scheduled tasks (none defined yet; present for future use) | — |
| `postgres` | Postgres 16 + pgvector | 5432 |
| `redis` | Celery broker/result backend + WebSocket pub/sub | 6379 |
| `minio` | S3-compatible object storage for uploaded documents | 9000 (API), 9001 (console) |
| `prometheus` | metrics scraping/storage | 9090 |
| `grafana` | dashboards over Prometheus | 3001 |
| `celery-exporter` | Celery → Prometheus metrics sidecar | — (internal only) |
| `postgres-exporter` | Postgres → Prometheus metrics sidecar | — (internal only) |
| `ollama` | optional local LLM runtime (`--profile local-ai`) | 11434 |

Services with no host port are still reachable from each other over the `dra-network` bridge
network by service name (e.g. `redis:6379`) — only the ones a human needs to reach directly are
published to the host.

## 4. Running fully local (no API keys)

```bash
docker compose --profile local-ai up -d --build
docker compose exec ollama ollama pull llama3.2
```

Set `AI_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`, `OLLAMA_MODEL=llama3.2` in `.env`
(note the hostname is the *service* name `ollama`, not `localhost` — containers resolve each other
by service name on `dra-network`) and restart `backend`/`worker` to pick up the change:

```bash
docker compose up -d backend worker
```

The `--profile local-ai` flag is required both times `ollama` needs to exist — Compose profiles are
opt-in per invocation, not persisted.

## 5. Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`docker-compose.prod.yml` (see that file for the full diff) removes dev bind-mounts and hot-reload,
stops publishing the data-layer ports (`postgres`/`redis`/`backend`) to the host — only `nginx`
(and `minio`'s console) stay reachable directly — runs the backend with 4 Uvicorn workers and the
Celery worker with concurrency 4, and adds per-service CPU/memory limits. Migrations and seeding
are still separate, explicit steps (§ 2) — nothing about `--prod` changes that.

**Before the first prod build**, update `NEXT_PUBLIC_API_BASE_URL`/`NEXT_PUBLIC_WS_BASE_URL` in
`.env` to point at wherever Nginx is actually reachable (e.g. `https://your-domain/api/v1` and
`wss://your-domain/ws`, not the `.env.example` defaults, which target the dev setup's direct
`:8000` access). Next.js inlines these into the static client bundle at build time (see
`docker/frontend/Dockerfile`'s `builder` stage) — they're passed through as `--build-arg`s in
`docker-compose.prod.yml`, so changing `.env` after the image is already built has no effect;
rebuild (`--build`) if you change them.

### Enabling HTTPS

The default `docker/nginx/nginx.conf` is plain HTTP, matching local `docker compose up`.
`docker/nginx/nginx.prod.conf.example` is a complete, ready-to-adapt config with a `:443` server
block (TLS 1.2/1.3, HSTS, HTTP→HTTPS redirect) — no certificate is generated or committed here (a
fake self-signed one would be misleading; a real one needs a real domain and an ACME client this
repo can't run on your behalf). To use it:

1. Obtain a certificate however suits your environment (`certbot`, an ACME sidecar, or terminate
   TLS at a cloud load balancer in front of Nginx instead and skip this entirely).
2. Copy `nginx.prod.conf.example` to `docker/nginx/nginx.conf` (or mount it in place via a compose
   override) and point `ssl_certificate`/`ssl_certificate_key` at your real cert/key.
3. Mount the certificate directory into the `nginx` service and publish port 443.

## 6. Common operations

```bash
make logs                        # tail every service
docker compose logs -f backend   # tail one service
make migrate                     # alembic upgrade head
make migrate-new name="..."      # generate a new migration
make seed                        # (re-)seed the agents reference table — idempotent
make shell-backend               # shell into the backend container
make shell-db                    # psql against the postgres container
docker compose down              # stop, keep volumes
docker compose down -v           # stop and delete all volumes (destroys data)
```

## 7. Troubleshooting

- **`worker` fails healthcheck / restarts repeatedly right after a fresh `up`**: the first
  `sentence-transformers`/`torch` import (BGE embeddings) inside a freshly built worker image can
  take a while depending on host CPU — give it a couple of minutes before assuming it's actually
  stuck; `docker compose logs worker` will show real progress (HuggingFace Hub calls, model
  loading) if it's just slow rather than broken.
- **`backend`/`frontend`/`nginx` stuck "starting" (not yet healthy)**: dependent services wait on
  `condition: service_healthy` (see `docker-compose.yml`), so this is often a symptom of an
  earlier service (`postgres`/`redis`/`minio`, or `backend` itself for `frontend`/`nginx`) never
  reaching healthy — check that service's own logs first.
- **A document never leaves `pending`/`processing`**: confirm `worker` is actually running
  (`docker compose ps`) and that its logs show the `knowledge_base.process_document` task being
  received — an unhealthy/crashed worker leaves documents stuck exactly this way.
- **Port already in use**: another process on the host (or a previous, not-fully-torn-down Compose
  project) is using one of the ports in § 1 — override the conflicting `*_PORT`/`*_EXPOSED_PORT`
  variable in `.env` rather than stopping the other process.
- **Grafana shows "No data"**: Prometheus scrapes every 15s (`docker/prometheus/prometheus.yml`) —
  give it a minute after first `up`, and confirm each target is `UP` at
  http://localhost:9090/targets before assuming the dashboard itself is wrong.
