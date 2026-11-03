.DEFAULT_GOAL := help
.PHONY: help env dev down logs install hooks lint lint-backend lint-frontend format test test-backend test-frontend build-frontend precommit

BACKEND  := uv run --directory backend
FRONTEND := npm --prefix frontend run -s
PRE_COMMIT := uvx pre-commit@4.7.0

help: ## List targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

env: ## Create .env from .env.example if it doesn't exist
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

dev: env ## Start the full stack (postgres, redis, api, frontend)
	docker compose up --build --wait
	@echo "API: http://localhost:8000/health   Web: http://localhost:3000"

down: ## Stop the stack (keeps data volumes)
	docker compose down

logs: ## Follow logs from all services
	docker compose logs -f

install: ## Install backend + frontend deps from lockfiles, then git hooks
	cd backend && uv sync --frozen
	cd frontend && npm ci
	$(MAKE) hooks

hooks: ## Install pre-commit git hooks
	$(PRE_COMMIT) install

lint: lint-backend lint-frontend ## All linters, formatters (check mode) and type checkers

lint-backend:
	cd backend && uv lock --check
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) mypy

lint-frontend:
	$(FRONTEND) lint
	$(FRONTEND) typecheck
	$(FRONTEND) format:check

format: ## Auto-fix lint and formatting
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .
	$(FRONTEND) format

test: test-backend test-frontend ## All default test suites (no live/eval)

test-backend:
	$(BACKEND) pytest

test-frontend:
	$(FRONTEND) test

build-frontend: ## Production build of the Next.js app
	$(FRONTEND) build

precommit: ## Run every pre-commit hook on all files
	$(PRE_COMMIT) run --all-files
