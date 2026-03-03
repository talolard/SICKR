.PHONY: lint format format-check format-all typecheck test tidy preflight index web eval vss-index

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

index:
	uv run python -m tal_maria_ikea.ingest.index --strategy v2_metadata_first

web:
	uv run python -m tal_maria_ikea.web.runserver

eval:
	uv run python -m tal_maria_ikea.eval.run --index-run-id latest --k 10

vss-index:
	./scripts/build_vss_index.sh

# One command before commit.
tidy: format
	uv run ruff check --fix .
	uv run pyrefly check
	uv run pytest
