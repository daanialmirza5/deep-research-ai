# Roadmap

What's real today, what's explicitly planned next, and what's genuinely speculative — kept
separate on purpose. See [CHANGELOG.md](../CHANGELOG.md) for what shipped in each of the 15 build
phases, and [api-design.md](api-design.md) for the endpoint-level detail behind each "not yet
built" item below.

## Immediate: Phase 15 (GitHub polishing)

The one remaining phase of the original build plan: issue/PR templates, CI/license/coverage
badges wired to a real repository, a first tagged release, demo GIF/screenshots, and a populated
`assets/` directory. See [milestones.md](milestones.md) for its exit criteria.

## Near-term: gaps flagged during Phase 14's documentation audit

Each of these was found while reconciling the docs against the real code — real, scoped,
concrete gaps, not aspirational features invented for this list:

- **Report export** (Markdown/PDF/DOCX/HTML) — `report_exports` exists in the database schema and
  `POST /reports/{id}/export` is sketched in `api-design.md`, but nothing implements it. The
  Reports page currently renders markdown in-browser only.
- **Session cancel/resume** — `POST /sessions/{id}/cancel` and `/resume` are sketched but not
  built. `research_sessions.graph_state` already persists a full checkpoint after every node, so
  resume is mostly "read it back into `graph.ainvoke()`, not currently plumbed" rather than a new
  storage design.
- **Report versioning UI** — `reports.version` is tracked on every row (a revision loop produces a
  new version), but nothing exposes the history; the Reports page only ever shows the latest.
- **Agent configuration** — `GET/PATCH /agents` (enable/disable an agent, adjust
  `max_revision_loops` at runtime) is sketched but not built. Today `max_revision_loops` is a
  deployment-time `Settings` value, not editable without a restart.
- **Project rename/archive/delete** — `PATCH`/`DELETE /projects/{id}` are sketched but not built.
- **Pagination and filtering** on every list endpoint — fine at the scale every live verification
  in this project has actually run at, not fine forever.
- **Idempotency-Key** on `POST /sessions` — a dropped connection during session creation can
  enqueue a duplicate pipeline run today.
- **Rate-limit storage** is in-memory (`slowapi`'s default) — a one-line `storage_uri` change to
  Redis once a real multi-replica deployment needs shared limit state (`docker-compose.prod.yml`
  currently runs a single `backend` replica, so this hasn't been a real constraint yet).

## Medium-term: the full Workspace visualization

`docs/ui-wireframes.md` § 5 sketches a 3-pane Workspace (an animated agent-workflow graph, a
dedicated source/citation panel with tabs, inline follow-up query refinement) considerably richer
than what Phase 12 actually built (a real, functional, but simpler progress checklist + streaming
trace — see that phase's `CHANGELOG.md` entry for the explicit scope-down rationale). Worth
revisiting once there's a concrete reason to invest in it — the current version is a genuinely
real, live-verified "submit → watch → read" flow, not a placeholder, and richer visualization is a
UX/polish upgrade to something that already works rather than a missing capability.

## Speculative / not currently planned

Ideas that would be reasonable directions but aren't scoped or committed:

- Additional LLM/embedding providers behind the existing `LLMProvider`/`EmbeddingProvider`
  interfaces (Gemini, Cohere, local GGUF models via `llama.cpp`).
- Additional search tools beyond the current DuckDuckGo/Arxiv/Wikipedia set (Semantic Scholar,
  Crossref, GitHub code search — all named in the original Phase 1 tech-stack sketch, not all
  built).
- Multi-user collaboration on a single project (shared sessions, comments on a report).
- A notification system (email/webhook) for long-running sessions instead of requiring the tab to
  stay open.
- Horizontal scaling guidance beyond the single-replica `docker-compose.prod.yml` — a real
  multi-node deployment guide (k8s manifests, or a managed-Postgres/Redis setup) once there's an
  actual deployment target that needs it.
