"""WebSocket relay for live agent progress (docs/api-design.md's WebSocket
section: `/ws/sessions/{id}`). app/workers/tasks.py publishes each pipeline
step to Redis pub/sub (app/core/pubsub.py); this endpoint subscribes to the
same channel and forwards events to the browser as they arrive.

Mounted at the app root (not under /api/v1) — see app/main.py — matching the
documented path. Auth is via a `token` query param rather than a header:
browsers' native WebSocket API cannot set arbitrary headers during the
handshake, so the access token travels in the URL instead (see
docs/api-design.md).
"""

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.config import get_settings
from app.core.container import Container
from app.core.exceptions import InvalidTokenError
from app.core.pubsub import subscribe_to_session
from app.core.security import decode_access_token
from app.repositories.research_session import ResearchSessionRepository

router = APIRouter(prefix="/ws")

_TERMINAL_STATUSES = {"completed", "failed"}


@router.websocket("/sessions/{session_id}")
async def session_events(websocket: WebSocket, session_id: uuid.UUID) -> None:
    token = websocket.query_params.get("token")
    settings = get_settings()
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user_id = decode_access_token(token, settings)
    except InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    container: Container = websocket.app.state.container
    async with container.db_sessionmaker() as db:
        research_session = await ResearchSessionRepository(db).get_by_id(session_id)

    # Same non-disclosure posture as ProjectNotFoundError/ResearchSessionNotFoundError
    # (app/services/exceptions.py): a session that doesn't exist and one that
    # belongs to someone else both just close the socket, no distinction.
    if (
        research_session is None
        or research_session.deleted_at is not None
        or research_session.user_id != user_id
    ):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        async for event in subscribe_to_session(container.redis, str(session_id)):
            await websocket.send_json(event)
            if event.get("type") == "status" and event.get("status") in _TERMINAL_STATUSES:
                break
    except WebSocketDisconnect:
        return
    await websocket.close()
