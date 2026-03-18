WORKTREE_ENV_FILE ?= .tmp_untracked/worktree.env

ifneq ("$(wildcard $(WORKTREE_ENV_FILE))","")
include $(WORKTREE_ENV_FILE)
endif

.PHONY: deps chat lint format format-check format-all typecheck test tidy preflight \
	ui-install ui-dev ui-dev-mock ui-dev-real ui-test ui-test-e2e ui-test-e2e-real \
	ui-test-e2e-real-ui-smoke dev-all dev-all-mock reset agent-start merge-list \
	merge-list-all merge-list-failing merge-list-json merge-normalize

HOST ?= 127.0.0.1
PORT ?= $(or $(BACKEND_PORT),8000)
UI_DIR ?= ui
UI_PORT ?= 3000
PY_AG_UI_URL ?= http://127.0.0.1:$(PORT)/ag-ui/

export AGENT_SLOT BACKEND_PORT HOST PORT UI_PORT PY_AG_UI_URL
export DUCKDB_PATH MILVUS_LITE_URI ARTIFACT_ROOT_DIR FEEDBACK_ROOT_DIR

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

ui-install:
	cd $(UI_DIR) && corepack enable && corepack prepare pnpm@10.6.3 --activate && pnpm install

ui-dev:
	cd $(UI_DIR) && pnpm dev --port $(UI_PORT)

ui-dev-mock:
	cd $(UI_DIR) && pnpm dev:mock --port $(UI_PORT)

ui-dev-real:
	cd $(UI_DIR) && NEXT_PUBLIC_USE_MOCK_AGENT=0 PY_AG_UI_URL=$(PY_AG_UI_URL) pnpm dev --port $(UI_PORT)

ui-test:
	cd $(UI_DIR) && pnpm test

ui-test-e2e:
	cd $(UI_DIR) && UI_PORT=$(UI_PORT) pnpm test:e2e

ui-test-e2e-real:
	cd $(UI_DIR) && UI_PORT=$(UI_PORT) PY_AG_UI_URL=$(PY_AG_UI_URL) pnpm test:e2e:real

ui-test-e2e-real-ui-smoke:
	@set -eu; \
	BACKEND_STARTED=0; \
	BACKEND_PID=""; \
	LOG_DIR="$${ARTIFACT_ROOT_DIR:-/tmp}"; \
	LOG_PATH="$$LOG_DIR/ikea-agent-ui-smoke-backend-$(PORT).log"; \
	mkdir -p "$$LOG_DIR"; \
	if curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
		echo "Backend already running at http://$(HOST):$(PORT)"; \
	else \
		echo "Backend not running; starting temporary backend on http://$(HOST):$(PORT)"; \
		ALLOW_MODEL_REQUESTS=0 uv run uvicorn ikea_agent.chat_app.main:create_app --factory --host $(HOST) --port $(PORT) >"$$LOG_PATH" 2>&1 & \
		BACKEND_PID=$$!; \
		BACKEND_STARTED=1; \
		trap 'if [ "$$BACKEND_STARTED" -eq 1 ] && [ -n "$$BACKEND_PID" ]; then kill "$$BACKEND_PID" 2>/dev/null || true; wait "$$BACKEND_PID" 2>/dev/null || true; fi' EXIT INT TERM; \
		i=0; \
		while [ "$$i" -lt 60 ]; do \
			if curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
				break; \
			fi; \
			i=$$((i + 1)); \
			sleep 1; \
		done; \
		if ! curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
			echo "Backend did not become ready; see $$LOG_PATH"; \
			exit 1; \
		fi; \
	fi; \
	cd $(UI_DIR) && UI_PORT=$(UI_PORT) RUN_REAL_BACKEND_E2E=1 PY_AG_UI_URL=http://$(HOST):$(PORT)/ag-ui/ pnpm playwright test --config playwright.real.config.ts --grep "sends and receives messages via CopilotKit UI"

dev-all:
	@set -e; \
	trap 'kill 0' INT TERM EXIT; \
	$(MAKE) chat & \
	sleep 2; \
	$(MAKE) ui-dev-real & \
	wait

dev-all-mock:
	@set -e; \
	trap 'kill 0' INT TERM EXIT; \
	$(MAKE) ui-dev-mock & \
	wait

reset:
	@lsof -tiTCP:$(UI_PORT) -sTCP:LISTEN | xargs kill 2>/dev/null || true
	@lsof -tiTCP:$(PORT) -sTCP:LISTEN | xargs kill 2>/dev/null || true
	@rm -rf $(UI_DIR)/.next 2>/dev/null || true
	@echo "Stopped dev servers on :$(UI_PORT)/:$(PORT) and cleared $(UI_DIR)/.next"

agent-start:
	@if [ -n "$(ISSUE)" ]; then \
		./scripts/worktree/start-task.sh --issue "$(ISSUE)" --slot "$(SLOT)"; \
	elif [ -n "$(QUERY)" ]; then \
		./scripts/worktree/start-task.sh --query "$(QUERY)" --slot "$(SLOT)"; \
	else \
		echo "Usage: make agent-start SLOT=<0-99> ISSUE=<id> OR QUERY=\"text\""; \
		exit 1; \
	fi

merge-list:
	./scripts/beads/merge_list.sh

merge-list-all:
	./scripts/beads/merge_list.sh --all

merge-list-failing:
	./scripts/beads/merge_list.sh --failing

merge-list-json:
	./scripts/beads/merge_list.sh --json

merge-normalize:
	./scripts/beads/merge_normalize.sh

# One command before commit.
tidy: format
	uv run ruff check --fix .
	uv run pyrefly check
	uv run pytest
