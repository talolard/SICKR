.PHONY: deps chat lint format format-check format-all typecheck test tidy preflight

HOST ?= 127.0.0.1
PORT ?= 8000

deps:
	uv sync --all-groups

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

format-all: format
	uv run ruff check --fix .
	uv run ruff format --check .
	uv run pyrefly check

typecheck:
	uv run pyrefly check

test:
	uv run pytest

preflight:
	./scripts/preflight.sh

chat:
	uv run uvicorn ikea_agent.chat_app.main:create_app --factory --host $(HOST) --port $(PORT) --reload

# One command before commit.
tidy: format
	uv run ruff check --fix .
	uv run pyrefly check
	uv run pytest
