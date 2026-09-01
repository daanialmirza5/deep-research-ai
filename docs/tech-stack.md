# Tech Stack & Justification

Every choice below is made against three criteria: (1) does it let a solo/small team ship a
production system without reinventing infrastructure, (2) does it stay swappable so no single
vendor or library choice locks the architecture in, and (3) does it read as a credible,
current stack to a senior engineer or ML infra hiring panel.

## Frontend

| Choice | Why |
|---|---|
| **Next.js (App Router)** | Server components for the dashboard shell, streaming SSR for the research workspace, file-based routing keeps the enterprise nav (sidebar + nested workspace routes) simple. Same framework recruiters expect from a modern SaaS. |
| **TypeScript** | Non-negotiable at this scope — agent state, WebSocket event payloads, and report schemas are shared contracts with the backend; type safety catches drift early. |
| **TailwindCSS** | Utility-first styling scales across ~15 screens without a bespoke CSS architecture; pairs directly with shadcn. |
| **shadcn/ui** | Unstyled, composable primitives (Radix under the hood) instead of a heavy component library — needed for a Linear/Vercel-grade custom look rather than "looks like Material UI." |
| **Framer Motion** | Agent workflow visualization (nodes lighting up as they execute) is inherently animation-driven; Framer Motion is the standard choice for orchestrated, physics-based transitions in React. |
| **TanStack Query** | Server-state cache for REST calls (projects, sessions, reports) with built-in retry/staleness handling, separate from local UI state. WebSocket agent events are pushed into the same cache via `queryClient.setQueryData`. |

## Backend

| Choice | Why |
|---|---|
| **FastAPI** | Async-first, native Pydantic validation, auto-generated OpenAPI — required for a documented, versioned REST API and for streaming agent events over WebSocket/SSE. |
| **Python** | The AI/agent ecosystem (LangGraph, LangChain, HF, PyPDF, python-docx) is Python-native; using a second language for AI orchestration would fragment the codebase for no benefit. |
| **uv** (dependency manager) | The LangGraph/LangChain dependency graph is large (~140 packages); measured directly during Phase 2 verification, pip's backtracking resolver took 3+ minutes (and once appeared to hang) on this exact graph, while uv resolved and installed it in under 10 seconds. Used in the Dockerfiles (`docker/backend/`, `docker/worker/`) and `make install-backend`; `backend/pyproject.toml` remains the single source of truth for dependencies either tool reads. |
| **Celery + Redis** | Research runs are long (multi-minute, multi-agent, multi-tool-call). They cannot live inside an HTTP request/response cycle. Celery workers execute the LangGraph pipeline asynchronously; Redis is both the broker and the pub/sub channel that streams intermediate agent state back to the API for WebSocket relay. |

## AI / Orchestration

| Choice | Why |
|---|---|
| **LangGraph** | The agent pipeline is a graph, not a chain — Reviewer can loop back to Writer, Fact Checker can loop back to Research. LangGraph models this natively as a stateful graph with conditional edges, checkpointing, and resumability. Plain LangChain chains cannot express cycles cleanly. |
| **LangChain** | Document loaders and text splitters (Phase 10) — not the LLM/embedding abstraction layer. Phase 7 hand-rolled a minimal `LLMProvider`/`EmbeddingProvider` ABC (`ai/llm/`, `ai/embeddings/`) directly over each vendor's native SDK (`openai`, `anthropic`, `ollama`) instead: one fewer abstraction layer between our code and the actual API, full control over the exact request/response shape, and no exposure to LangChain's chat-model interface changing under us. LangGraph (the orchestrator) only needs plain Python callables for graph nodes — it has no dependency on LangChain's model abstractions either. |
| **OpenAI / Anthropic / Ollama** | Three providers behind one `LLMProvider` interface (strategy pattern, see [architecture.md](architecture.md)). OpenAI/Anthropic for hosted quality, Ollama so the entire pipeline can run fully offline/local with zero API cost — a real differentiator for a portfolio project ("works locally" is a stated goal). |
| **HuggingFace (transformers)** | Backing runtime for local BGE embeddings and any local re-ranking model, keeping the "local-first" path fully self-hosted. |

## Embeddings & Vector Store

| Choice | Why |
|---|---|
| **BGE (BAAI/bge-*)** | Best open-weight embedding family for retrieval at the time of writing; runs locally via HuggingFace, no API key required — this is the default embedding path. |
| **OpenAI Embeddings** | Swappable alternative behind the same `EmbeddingProvider` interface for higher-quality hosted embeddings when an API key is configured. |
| **pgvector** | Vector storage lives *inside* PostgreSQL instead of a separate vector DB (Pinecone/Weaviate/Qdrant). One database to operate, back up, and reason about transactionally — a document row and its embedding are written in the same transaction. Acceptable trade-off at this scale (single-tenant/small-team SaaS, not billion-vector scale). |

## Database

| Choice | Why |
|---|---|
| **PostgreSQL** | Relational integrity for users/projects/sessions/reports plus `pgvector` extension for embeddings, plus JSONB columns for flexible agent-run metadata — one engine covers relational, vector, and semi-structured needs. |

## Authentication

| Choice | Why |
|---|---|
| **JWT (access + refresh)** | Stateless auth for the REST API and WebSocket handshake; short-lived access tokens, rotating refresh tokens stored hashed (SHA-256) in Postgres — the refresh token itself is a high-entropy opaque string, not a JWT, so a stolen DB dump doesn't hand out valid refresh tokens the way a stolen signing key would. |
| **`bcrypt` (direct, not via passlib)** | Password hashing. Phase 5 hit a real crash: passlib's `CryptContext` runs its own bcrypt self-test with a fixed vector at first use, which raises `ValueError` against `bcrypt>=4.1`'s stricter >72-byte rejection — a known, unresolved passlib/bcrypt incompatibility (passlib is effectively unmaintained). Calling `bcrypt.hashpw`/`checkpw` directly removes the broken abstraction layer entirely. |
| **OAuth (Google/GitHub)** | Standard SaaS login reducing signup friction; implemented as an additional identity provider feeding the same JWT issuance path, not a replacement for it. |

## Storage

| Choice | Why |
|---|---|
| **MinIO** | S3-compatible object storage for uploaded PDFs/DOCX and exported reports. S3-compatible API means the same code path deploys against real AWS S3 in production with only a config change. |

## Monitoring

| Choice | Why |
|---|---|
| **Prometheus** | Scrapes FastAPI (via `prometheus-fastapi-instrumentator`) and Celery (via `celery-exporter`) for request latency, queue depth, and per-agent execution time. |
| **Grafana** | Dashboards over Prometheus for the analytics/observability story — also demonstrates production-operations maturity, not just feature code. |

## Infrastructure

| Choice | Why |
|---|---|
| **Docker / Docker Compose** | Every service (frontend, backend, worker, Postgres, Redis, MinIO, Prometheus, Grafana, Nginx) runs identically on a laptop and in the cloud — satisfies the "works locally" and "supports Docker" goals simultaneously. |
| **Nginx** | Single reverse-proxy entry point; TLS termination and routing between the Next.js frontend and FastAPI backend in production. |
| **GitHub Actions** | CI (lint, type-check, test) on every PR; CD workflow builds and pushes images on tag. Required for the "GitHub portfolio quality" bar — a repo without green CI checks reads as unfinished. |

## Replaceability matrix

This is what "each component should be independently replaceable" means concretely:

| Interface | Implementations shipped | Swap mechanism |
|---|---|---|
| `LLMProvider` | OpenAI, Anthropic, Ollama | Strategy pattern, chosen via `AI_PROVIDER` env var, injected via DI container |
| `EmbeddingProvider` | BGE (local), OpenAI | Same pattern, `EMBEDDING_PROVIDER` env var |
| `VectorStore` | pgvector | Interface allows a future Qdrant/Pinecone adapter without touching agent code |
| `ObjectStorage` | MinIO | S3-compatible; same client works against AWS S3 |
| `SearchTool` | Google, DuckDuckGo, Arxiv, Crossref, Semantic Scholar, Wikipedia, GitHub | Each is a `BaseTool` subclass registered in a tool registry; Research Agent is agnostic to which tools exist |
| `DocumentLoader` | PDF, DOCX, TXT, CSV, Markdown, URL, YouTube | Each a `BaseLoader` subclass keyed by MIME type/extension in a loader registry |
