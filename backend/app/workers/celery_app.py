"""Celery application instance — the counterpart to app.main:app for the
worker/beat containers (see docker-compose.yml). Startable as
`celery -A app.workers.celery_app worker`.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "deep_research_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Generous ceiling above a single agent's own timeout (settings.agent_timeout_seconds).
    task_time_limit=settings.agent_timeout_seconds * 6,
)

celery_app.autodiscover_tasks(["app.workers"])
