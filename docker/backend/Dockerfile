# Backend API image — deliberately lean: serves REST/WebSocket and enqueues
# Celery tasks, but never runs the agent graph itself, so it installs backend
# dependencies WITHOUT the `local` (torch/sentence-transformers) extra.
# The worker image (docker/worker/Dockerfile) is what carries that weight.
#
# Build context is the repo root (see docker-compose.yml: `context: .`) because
# this image needs both backend/ and the sibling ai/ package (imported via
# PYTHONPATH, not pip-installed — see docs/architecture.md's DI section).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/srv \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# uv resolves this project's LangGraph/LangChain dependency tree in single-digit
# seconds; pip's backtracking resolver was measured taking 3+ minutes (and in
# one run appeared to hang) on the same graph during Phase 2 verification.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 dra
WORKDIR /srv/backend

# Dependency layer: cached as long as pyproject.toml doesn't change, regardless
# of source edits. The placeholder package dir lets the editable install
# resolve; it's overwritten by the real source in the next layer (editable
# installs read from the live directory, so this is safe).
#
# backend/pyproject.toml's `readme = "../README.md"` resolves relative to
# pyproject.toml's own location (/srv/backend/pyproject.toml here), i.e.
# /srv/README.md — hatchling's editable-install build hard-fails
# (`OSError: Readme file does not exist`) without it; found only by actually
# running `uv pip install -e .` against this exact layout outside Docker,
# not by reading the Dockerfile.
COPY README.md /srv/README.md
COPY backend/pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py && uv pip install -e .

# Source layer. alembic.ini/alembic/ are needed too — `make migrate` runs
# `docker compose exec backend alembic upgrade head` against this image, not
# a separate migration image, so they can't be left out the way they were
# when this Dockerfile was first written (Phase 2, before Phase 4 added them).
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY ai /srv/ai

USER dra
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
