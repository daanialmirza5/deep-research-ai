.DEFAULT_GOAL := help
COMPOSE := docker compose

.PHONY: help up down restart logs build ps \
        install install-backend install-frontend \
        migrate migrate-new seed \
        test test-backend test-frontend test-e2e lint fmt \
        shell-backend shell-db clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## --- Environment lifecycle -------------------------------------------------

up: ## Start the full stack (detached)
	$(COMPOSE) up -d --build

down: ## Stop the stack and remove containers
	$(COMPOSE) down

restart: down up ## Restart the full stack

logs: ## Tail logs for all services
	$(COMPOSE) logs -f --tail=200

ps: ## Show running services
	$(COMPOSE) ps

build: ## Rebuild all images
	$(COMPOSE) build

## --- Dependencies -----------------------------------------------------------

install: install-backend install-frontend ## Install backend + frontend dependencies locally

install-backend: ## Install backend (+ai) dependencies into the active Python environment (uv resolves this dependency tree in seconds; pip's resolver has been observed taking minutes on the same graph)
	# `local` (sentence-transformers/torch, for BGE embeddings) is included because
	# EMBEDDING_PROVIDER=bge is the default and native local dev (docs/installation.md)
	# runs the Celery worker directly, not just through docker/worker/Dockerfile's own
	# separate install of the same extra — omitting it here left `make install` unable
	# to actually run the default configuration.
	uv pip install -e "./backend[dev,local]"

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

## --- Database ---------------------------------------------------------------

migrate: ## Apply database migrations
	$(COMPOSE) exec backend alembic upgrade head

migrate-new: ## Generate a new migration: make migrate-new name="add reports table"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(name)"

seed: ## Load development seed data
	$(COMPOSE) exec backend python -m app.scripts.seed

## --- Quality ------------------------------------------------------------

test: test-backend test-frontend ## Run backend + frontend test suites

test-backend: ## Run pytest (backend + ai)
	cd backend && pytest

test-frontend: ## Run frontend unit/component tests
	cd frontend && npm test

test-e2e: ## Run end-to-end tests (Playwright, requires the stack running)
	npx playwright test

lint: ## Lint backend (ruff) and frontend (eslint)
	cd backend && ruff check .
	cd frontend && npm run lint

fmt: ## Auto-format backend (ruff) and frontend (prettier)
	cd backend && ruff format .
	cd frontend && npm run format

## --- Debugging ----------------------------------------------------------

shell-backend: ## Open a shell in the running backend container
	$(COMPOSE) exec backend bash

shell-db: ## Open a psql shell against the running postgres container
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

clean: ## Remove containers, volumes, and dangling images for this project
	$(COMPOSE) down -v --remove-orphans
