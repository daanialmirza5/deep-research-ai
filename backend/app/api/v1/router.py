"""Versioned API mount point — every business resource router is included
here, keyed to the prefix/tag it owns in docs/api-design.md § endpoint
catalog. Mounted under /api/v1 in app/main.py.
"""

from fastapi import APIRouter

from app.api.v1 import analytics, auth, documents, knowledge_base, projects, sessions, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(sessions.router, tags=["sessions"])
# knowledge_base.router/documents.router/analytics.router declare their own
# full paths ("/knowledge-base/search", "/documents/upload",
# "/projects/{id}/documents", "/analytics/overview") rather than taking a
# prefix here, matching sessions.router's pattern.
api_router.include_router(knowledge_base.router, tags=["knowledge-base"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(analytics.router, tags=["analytics"])

# Phase 8:  api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
# Phase 7:  api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
