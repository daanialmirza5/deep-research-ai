# Repository Structure

The full target tree (as it will exist once every phase through Phase 15 is complete). Only
`docs/` (this Phase 1 planning set) exists today — everything else below is a plan, populated
incrementally starting Phase 2. Directories are annotated with what they'll hold and why they're
separated the way they are.

```
deep-research-ai/
├── README.md                    # project overview, quickstart, badges
├── LICENSE                      # MIT
├── CHANGELOG.md                 # Keep a Changelog format, per-release
├── CONTRIBUTING.md              # dev setup, branch/PR conventions, commit style
├── CODE_OF_CONDUCT.md           # Contributor Covenant
├── SECURITY.md                  # vuln disclosure policy
├── .env.example                 # every env var consumed by any service, documented inline
├── docker-compose.yml           # local dev: all services
├── docker-compose.prod.yml      # prod overrides (no bind mounts, resource limits)
├── Makefile                     # make up / down / migrate / test / lint / seed
│
├── frontend/                    # Next.js app
│   ├── app/                     # App Router: (auth)/, (dashboard)/, landing, globals.css
│   ├── components/              # shared UI (hand-written shadcn-style primitives) + layout/
│   ├── features/                # feature-scoped modules — added starting Phase 8 once
│   │                             # workspace/kb/analytics have real data to be feature-scoped around
│   ├── hooks/                   # TanStack Query hooks (use-auth.ts; a WS hook lands in Phase 8)
│   ├── lib/                     # api-client, auth (token storage), query-client, utils, types
│   ├── tests/                   # tests/lib (vitest unit) + tests/e2e (Playwright)
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                     # FastAPI app — clean architecture layering
│   ├── app/
│   │   ├── api/v1/              # controllers/routers only — no business logic
│   │   ├── services/            # business logic, calls into ai/ and repositories/
│   │   ├── repositories/        # SQLAlchemy query encapsulation
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/              # Pydantic request/response DTOs
│   │   ├── core/                # config, security, DI container, logging setup
│   │   ├── middlewares/         # auth, rate limit, request logging, error handler
│   │   ├── workers/              # Celery task definitions (thin wrappers calling services)
│   │   └── utils/
│   ├── alembic/                 # migrations
│   ├── tests/                   # pytest: unit + integration
│   ├── pyproject.toml
│   └── celery_app.py
│
├── ai/                           # standalone agent/orchestration package
│   │                             # (imported by backend/app/services, never imports from backend/)
│   ├── graph/
│   │   ├── state.py              # ResearchState (TypedDict) — the shared state every node reads/writes
│   │   ├── build.py               # build_research_graph(llm, embeddings, max_revision_loops=...)
│   │   └── routing.py              # conditional-edge predicates, standalone so they're unit-testable
│   │                                # without running the whole graph (see ai/tests/test_routing.py)
│   ├── agents/                   # one module per agent, each implementing BaseAgent (ai/agents/base.py)
│   │   ├── base.py                # BaseAgent ABC
│   │   ├── planner.py             # real LLM call (Phase 7); richer planning is Phase 8
│   │   ├── research.py            # stub — real search tools land in Phase 8
│   │   ├── retriever.py           # real embedding call (Phase 7); real vector search is Phase 9
│   │   ├── summarizer.py          # stub
│   │   ├── fact_checker.py        # stub — always verifies until Phase 8
│   │   ├── writer.py              # real LLM call (Phase 7); real synthesis is Phase 8
│   │   ├── reviewer.py            # stub — always approves until Phase 8
│   │   ├── citation.py            # stub
│   │   ├── evaluation.py          # stub
│   │   └── memory.py              # stub — real KB persistence is Phase 9/10
│   ├── tools/                    # search tool implementations (BaseTool subclasses) — Phase 8
│   │   ├── web_search.py         # Google / DuckDuckGo
│   │   ├── arxiv.py
│   │   ├── semantic_scholar.py
│   │   ├── crossref.py
│   │   ├── wikipedia.py
│   │   └── github.py
│   ├── loaders/                  # document loaders (BaseLoader subclasses) — Phase 10
│   │   ├── pdf_loader.py
│   │   ├── docx_loader.py
│   │   ├── markdown_loader.py
│   │   ├── csv_loader.py
│   │   ├── url_loader.py
│   │   └── youtube_loader.py
│   ├── llm/                      # LLMProvider ABC + OpenAI/Anthropic/Ollama, each over the vendor's
│   │   │                          # native SDK directly (see docs/tech-stack.md's LangChain entry for why)
│   │   ├── base.py                # LLMProvider ABC, LLMMessage
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── ollama_provider.py
│   │   └── factory.py             # get_llm_provider(settings) — the only module importing all three SDKs
│   ├── embeddings/                # EmbeddingProvider ABC + BGE (local, default) / OpenAI
│   │   ├── base.py
│   │   ├── bge_provider.py         # sentence-transformers; only imported when actually selected —
│   │   │                            # see app/core/container.py's lazy `embeddings` property
│   │   ├── openai_provider.py
│   │   └── factory.py
│   ├── memory/                    # long-term memory store interface -> pgvector — Phase 9/10
│   ├── prompts/                   # versioned prompt templates per agent — Phase 8
│   ├── evaluation/                 # scoring rubrics for Evaluation Agent — Phase 8
│   └── tests/
│
├── database/                     # schema documentation/review layer (see database/README.md)
│   ├── seeds/                     # dev seed data
│   └── schema.sql                 # generated reference dump for quick review
│
├── docs/                          # (this Phase 1 deliverable, continues to grow every phase)
│   ├── architecture.md
│   ├── tech-stack.md
│   ├── database-schema.md
│   ├── api-design.md
│   ├── ui-wireframes.md
│   ├── folder-structure.md
│   ├── milestones.md
│   ├── installation.md            # added Phase 2
│   ├── deployment.md               # added Phase 13
│   ├── api/                        # generated OpenAPI reference, added Phase 3
│   └── diagrams/                   # exported PNG/SVG versions of mermaid diagrams for README
│
├── tests/                          # end-to-end tests spanning frontend+backend (Playwright)
│
├── docker/                         # per-service Dockerfiles + nginx.conf, prometheus.yml, grafana provisioning
│   ├── frontend/Dockerfile
│   ├── backend/Dockerfile
│   ├── worker/Dockerfile
│   ├── nginx/nginx.conf
│   ├── prometheus/prometheus.yml
│   └── grafana/provisioning/
│
├── .github/
│   ├── workflows/                  # ci.yml, cd.yml, security-scan.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── scripts/                        # setup.sh, seed_db.py, generate_er_diagram.py, etc.
│
└── assets/                         # logo, README screenshots, architecture diagram exports
```

## Rationale for the top-level split

- **`ai/` is a sibling of `backend/`, not nested inside it.** The agent/orchestration logic has no
  FastAPI dependency and should be testable, importable, and — long-term — publishable as a
  standalone package independent of the web layer. `backend/app/services/research_service.py`
  imports from `ai/`, never the reverse.
- **`database/` vs `backend/alembic/`**: `backend/alembic/` is the *runtime* migration tool
  (what actually runs against a live DB). `database/` is the *documentation and review* layer —
  a human-reviewable `schema.sql` snapshot and seed fixtures — so schema review in a PR doesn't
  require reading Alembic's autogenerated diff syntax.
- **`docker/` holds Dockerfiles per service** rather than one Dockerfile at repo root, because
  each service (frontend/backend/worker) has a different base image and build context; a single
  root Dockerfile would force awkward multi-stage gymnastics.
- **`tests/` at root is end-to-end only** (Playwright, spanning the whole stack); unit/integration
  tests live next to the code they test (`frontend/tests/`, `backend/tests/`, `ai/tests/`) so they
  run fast and scoped in CI, while `tests/` runs the slower full-stack suite in its own CI job.
