"""Pub/sub helper for streaming agent-execution events from the Celery
worker (app/workers/tasks.py) to the API's WebSocket relay (app/api/ws.py).
A thin shared convention — channel naming and the JSON envelope shape — so
neither side has to import the other; they just agree on a channel name.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from redis.asyncio import Redis


def session_channel(session_id: str) -> str:
    return f"session:{session_id}:events"


async def publish_event(redis: Redis, session_id: str, event: dict[str, Any]) -> None:
    await redis.publish(session_channel(session_id), json.dumps(event))


async def subscribe_to_session(redis: Redis, session_id: str) -> AsyncIterator[dict[str, Any]]:
    pubsub = redis.pubsub()
    await pubsub.subscribe(session_channel(session_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(session_channel(session_id))
        await pubsub.aclose()  # type: ignore[no-untyped-call]  # redis-py's own stub is incomplete here
