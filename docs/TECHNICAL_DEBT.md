# Deep Research AI — Technical Debt & Architectural Audit

**Repository**: `deep-research-ai`  

## Prioritized Debt Items
- **[P1 — High] Streaming WebSocket Updates for Agent Steps**: Current frontend waits for full report completion. Add fine-grained LangGraph streaming tokens and active agent status.
- **[P2 — Medium] Persistent Vector Store for Multi-Session Knowledge**: Memory is currently ephemeral per run; connect Qdrant / pgvector for cross-session knowledge reuse.
- **[P3 — Low] Local PDF & ArXiv Parser Integration**: Add specialized document ingestion for academic papers.
