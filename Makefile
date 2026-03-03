.PHONY: deps init db-init db-load db-reset index vss-index web eval eval-generate eval-labels demo \
	lint format format-check format-all typecheck test tidy preflight

DB_PATH ?= data/ikea.duckdb
CSV_PATH ?= data/IKEA_product_catalog.csv
HOST ?= 127.0.0.1
PORT ?= 8000
INDEX_STRATEGY ?= v2_metadata_first
INDEX_LIMIT ?=
INIT_INDEX_LIMIT ?= 100
INDEX_FLAGS ?=
EVAL_RUN_ID ?= latest
EVAL_K ?= 10
EVAL_SUBSET_ID ?= phase1_de_v1
EVAL_PROMPT_VERSION ?= p1_v1
EVAL_TARGET_COUNT ?= 200
EVAL_BATCH_SIZE ?= 25
EVAL_PARALLELISM ?= 4
EVAL_MAX_ROUNDS ?= 8
EVAL_LABEL_TOP_K ?= 3

deps:
	uv sync --all-groups

init: deps
	$(MAKE) db-reset
	$(MAKE) index INDEX_LIMIT=$(INIT_INDEX_LIMIT)
	$(MAKE) eval-generate
	$(MAKE) eval-labels

db-init:
	./scripts/init_duckdb.sh $(DB_PATH)

db-load:
	./scripts/load_ikea_data.sh $(DB_PATH) $(CSV_PATH)

db-reset:
	rm -f $(DB_PATH)
	$(MAKE) db-init db-load

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
	uv run python -m tal_maria_ikea.ingest.index --strategy $(INDEX_STRATEGY) $(if $(INDEX_LIMIT),--subset-limit $(INDEX_LIMIT),) $(INDEX_FLAGS)

web:
	uv run python -m tal_maria_ikea.web.runserver --host $(HOST) --port $(PORT)

eval:
	uv run python -m tal_maria_ikea.eval.run --index-run-id $(EVAL_RUN_ID) --k $(EVAL_K)

eval-generate:
	uv run python -m tal_maria_ikea.eval.generate --subset-id $(EVAL_SUBSET_ID) --prompt-version $(EVAL_PROMPT_VERSION) --target-count $(EVAL_TARGET_COUNT) --batch-size $(EVAL_BATCH_SIZE) --parallelism $(EVAL_PARALLELISM) --max-rounds $(EVAL_MAX_ROUNDS)

eval-labels:
	uv run python -m tal_maria_ikea.eval.bootstrap_labels --subset-id $(EVAL_SUBSET_ID) --prompt-version $(EVAL_PROMPT_VERSION) --top-k $(EVAL_LABEL_TOP_K)

vss-index:
	./scripts/build_vss_index.sh $(DB_PATH) cosine

demo: init web

# One command before commit.
tidy: format
	uv run ruff check --fix .
	uv run pyrefly check
	uv run pytest
