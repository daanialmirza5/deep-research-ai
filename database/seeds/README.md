# Seeds

`agents` reference table — one row per agent type (planner, research, retriever, summarizer,
fact_checker, writer, reviewer, citation, evaluation, memory), matching `ai.graph.state.AgentName`
and the graph wiring in `ai/graph/build.py` exactly.

Implemented as `backend/app/scripts/seed.py` (idempotent — safe to re-run) rather than a static
SQL file, so it can be run consistently against dev/CI/staging without a separate SQL-vs-ORM
drift risk. Load it via `make seed`.
