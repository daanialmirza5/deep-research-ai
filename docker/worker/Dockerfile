# Celery worker/beat image — runs the LangGraph agent pipeline and local
# embedding generation, so (unlike docker/backend/Dockerfile) it installs the
# `local` extra (sentence-transformers/torch) for the default BGE embedding
# path. Same base source as the backend image; only the dependency set and
# entrypoint differ (see docker-compose.yml: worker/beat `command:` overrides).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 dra
WORKDIR /srv/backend

# See docker/backend/Dockerfile's identical line for why README.md has to be
# copied in — hatchling's editable-install build reads pyproject.toml's
# `readme = "../README.md"` even here, and hard-fails without it.
COPY README.md /srv/README.md
COPY backend/pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py && uv pip install -e ".[local]"

COPY backend/app ./app
COPY ai /srv/ai

USER dra
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD celery -A app.workers.celery_app inspect ping -d celery@$HOSTNAME || exit 1
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"]
