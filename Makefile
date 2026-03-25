WORKTREE_ENV_FILE ?= .tmp_untracked/worktree.env
HUMAN_DEV_SLOT ?= 90

ifneq ("$(wildcard $(WORKTREE_ENV_FILE))","")
include $(WORKTREE_ENV_FILE)
endif

.PHONY: deps deps-up deps-down deps-reset deps-reseed deps-status chat lint format format-check format-all typecheck test tidy preflight \
	backend-coverage frontend-coverage coverage coverage-clean \
	ui-install ui-ensure-install ui-lint ui-typecheck ui-validate ui-dev ui-dev-mock \
	ui-dev-real ui-test ui-test-e2e ui-test-e2e-real ui-test-e2e-real-ui-smoke \
	deploy-migrate deploy-bootstrap deploy-verify-seed \
	dev human dev-human dev-all dev-all-mock reset agent-start agent-start-docs merge-list merge-list-all \
	merge-list-failing merge-list-json merge-normalize

HOST ?= 127.0.0.1
PORT ?= $(or $(BACKEND_PORT),8000)
UI_DIR ?= ui
UI_PORT ?= 3000
UI_NODE_MODULES ?= $(UI_DIR)/node_modules
PY_AG_UI_URL ?= http://127.0.0.1:$(PORT)/ag-ui/
DATABASE_URL ?= postgresql+psycopg://ikea:ikea@127.0.0.1:15432/ikea_agent
ARTIFACT_ROOT_DIR ?= data/artifacts
FEEDBACK_ROOT_DIR ?= comments
TRACE_ROOT_DIR ?= traces
UV := env -u VIRTUAL_ENV uv
UV_RUN := $(UV) run
COVERAGE_DIR ?= .tmp_untracked/coverage
BACKEND_COVERAGE_JSON ?= $(COVERAGE_DIR)/backend-coverage.json
BACKEND_COVERAGE_XML ?= $(COVERAGE_DIR)/backend-coverage.xml
FRONTEND_COVERAGE_DIR ?= $(UI_DIR)/coverage
FRONTEND_COVERAGE_SUMMARY ?= $(FRONTEND_COVERAGE_DIR)/coverage-summary.json
FRONTEND_COVERAGE_LCOV ?= $(FRONTEND_COVERAGE_DIR)/lcov.info
COVERAGE_SUMMARY_MD ?= $(COVERAGE_DIR)/summary.md
COVERAGE_REPORT_JSON ?= $(COVERAGE_DIR)/report.json
SMOKE_ASSISTANT_TEXT ?= Deterministic smoke response from the local test model.

export AGENT_SLOT BACKEND_PORT HOST PORT UI_PORT PY_AG_UI_URL
export DATABASE_URL ARTIFACT_ROOT_DIR FEEDBACK_ROOT_DIR TRACE_ROOT_DIR

deps:
	$(UV) sync --all-groups

deps-up:
	./scripts/worktree/deps.sh up --slot "$(SLOT)"

deps-down:
	./scripts/worktree/deps.sh down --slot "$(SLOT)"

deps-reset:
	./scripts/worktree/deps.sh reset --slot "$(SLOT)"

deps-reseed:
	./scripts/worktree/deps.sh reseed --slot "$(SLOT)"

deps-status:
	./scripts/worktree/deps.sh status --slot "$(SLOT)"

lint:
	$(UV_RUN) ruff check .

format:
	$(UV_RUN) ruff format .

format-check:
	$(UV_RUN) ruff format --check .

format-all: format
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff format --check .
	$(UV_RUN) pyrefly check

typecheck:
	$(UV_RUN) pyrefly check

test:
	$(UV_RUN) pytest

backend-coverage:
	mkdir -p $(COVERAGE_DIR)
	$(UV_RUN) pytest \
		--cov=src/ikea_agent \
		--cov=tests \
		--cov-report=term-missing \
		--cov-report=xml:$(BACKEND_COVERAGE_XML) \
		--cov-report=json:$(BACKEND_COVERAGE_JSON)

preflight:
	./scripts/preflight.sh

guard-full-bootstrap:
	@if [ "$(WORKTREE_BOOTSTRAP_MODE)" = "docs" ]; then \
		echo "This worktree is bootstrapped in docs mode and is not runnable yet."; \
		echo "Upgrade it first with: bash scripts/worktree/bootstrap.sh --mode full --slot <0-99>"; \
		exit 1; \
	fi

deploy-migrate:
	$(UV_RUN) python -m scripts.deploy.apply_migrations

deploy-bootstrap:
	$(UV_RUN) python -m scripts.deploy.bootstrap_catalog

deploy-verify-seed:
	$(UV_RUN) python -m scripts.deploy.verify_seed_state

chat: guard-full-bootstrap
	$(UV_RUN) uvicorn ikea_agent.chat_app.main:create_app --factory --host $(HOST) --port $(PORT) --reload

ui-install:
	cd $(UI_DIR) && corepack enable && corepack prepare pnpm@10.6.3 --activate && pnpm install

ui-ensure-install:
	@if [ ! -d "$(UI_NODE_MODULES)" ]; then \
		echo "UI dependencies are not installed in $(UI_DIR); bootstrapping them now."; \
		$(MAKE) ui-install; \
	fi

ui-lint: ui-ensure-install
	cd $(UI_DIR) && pnpm lint

ui-typecheck: ui-ensure-install
	cd $(UI_DIR) && pnpm typecheck

frontend-coverage: ui-ensure-install
	cd $(UI_DIR) && rm -rf coverage && pnpm exec vitest run --coverage

coverage-clean:
	rm -rf $(COVERAGE_DIR) $(FRONTEND_COVERAGE_DIR)

coverage: backend-coverage frontend-coverage
	mkdir -p $(COVERAGE_DIR)
	$(UV_RUN) python scripts/ci_coverage_report.py \
		--backend-json $(BACKEND_COVERAGE_JSON) \
		--frontend-summary $(FRONTEND_COVERAGE_SUMMARY) \
		--frontend-lcov $(FRONTEND_COVERAGE_LCOV) \
		--repo-root "$$(pwd)" \
		--summary-md $(COVERAGE_SUMMARY_MD) \
		--report-json $(COVERAGE_REPORT_JSON) \
		--fail-on-thresholds

ui-validate: ui-lint ui-typecheck frontend-coverage

ui-dev: guard-full-bootstrap
	cd $(UI_DIR) && pnpm dev --port $(UI_PORT)

ui-dev-mock: guard-full-bootstrap
	cd $(UI_DIR) && pnpm dev:mock --port $(UI_PORT)

ui-dev-real: guard-full-bootstrap
	cd $(UI_DIR) && NEXT_PUBLIC_USE_MOCK_AGENT=0 PY_AG_UI_URL=$(PY_AG_UI_URL) pnpm dev --port $(UI_PORT)

ui-test: ui-ensure-install
	cd $(UI_DIR) && pnpm test

ui-test-e2e:
	cd $(UI_DIR) && UI_PORT=$(UI_PORT) pnpm test:e2e

ui-test-e2e-real:
	cd $(UI_DIR) && UI_PORT=$(UI_PORT) PY_AG_UI_URL=$(PY_AG_UI_URL) pnpm test:e2e:real

ui-test-e2e-real-ui-smoke: guard-full-bootstrap
	@set -eu; \
	BACKEND_STARTED=0; \
	BACKEND_PID=""; \
	UI_STARTED=0; \
	UI_PID=""; \
	REPO_ROOT="$$(pwd)"; \
	LOG_DIR="$${ARTIFACT_ROOT_DIR:-/tmp}"; \
	BACKEND_LOG_PATH="$$LOG_DIR/ikea-agent-ui-smoke-backend-$(PORT).log"; \
	UI_LOG_PATH="$$LOG_DIR/ikea-agent-ui-smoke-ui-$(UI_PORT).log"; \
	mkdir -p "$$LOG_DIR"; \
	case "$$BACKEND_LOG_PATH" in \
		/*) ;; \
		*) BACKEND_LOG_PATH="$$REPO_ROOT/$$BACKEND_LOG_PATH" ;; \
	esac; \
	case "$$UI_LOG_PATH" in \
		/*) ;; \
		*) UI_LOG_PATH="$$REPO_ROOT/$$UI_LOG_PATH" ;; \
	esac; \
	if curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
		echo "Backend already running at http://$(HOST):$(PORT)"; \
	else \
		echo "Backend not running; starting temporary backend on http://$(HOST):$(PORT)"; \
			ALLOW_MODEL_REQUESTS=0 DETERMINISTIC_MODEL_RESPONSE_TEXT="$(SMOKE_ASSISTANT_TEXT)" uv run uvicorn ikea_agent.chat_app.main:create_app --factory --host $(HOST) --port $(PORT) >"$$BACKEND_LOG_PATH" 2>&1 & \
		BACKEND_PID=$$!; \
		BACKEND_STARTED=1; \
		trap 'if [ "$$UI_STARTED" -eq 1 ] && [ -n "$$UI_PID" ]; then kill "$$UI_PID" 2>/dev/null || true; wait "$$UI_PID" 2>/dev/null || true; fi; if [ "$$BACKEND_STARTED" -eq 1 ] && [ -n "$$BACKEND_PID" ]; then kill "$$BACKEND_PID" 2>/dev/null || true; wait "$$BACKEND_PID" 2>/dev/null || true; fi' EXIT INT TERM; \
		i=0; \
		while [ "$$i" -lt 60 ]; do \
			if curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
				break; \
			fi; \
			i=$$((i + 1)); \
			sleep 1; \
		done; \
		if ! curl -fsS "http://$(HOST):$(PORT)/api/agents" >/dev/null 2>&1; then \
			echo "Backend did not become ready; see $$BACKEND_LOG_PATH"; \
			exit 1; \
		fi; \
	fi; \
	if curl -fsS "http://$(HOST):$(UI_PORT)/agents/search" >/dev/null 2>&1; then \
		echo "UI already running at http://$(HOST):$(UI_PORT)"; \
	else \
		echo "UI not running; starting temporary UI on http://$(HOST):$(UI_PORT)"; \
		cd $(UI_DIR) && PY_AG_UI_URL=http://$(HOST):$(PORT)/ag-ui/ pnpm dev --port $(UI_PORT) >"$$UI_LOG_PATH" 2>&1 & \
		UI_PID=$$!; \
		UI_STARTED=1; \
		i=0; \
		while [ "$$i" -lt 60 ]; do \
			if curl -fsS "http://$(HOST):$(UI_PORT)/agents/search" >/dev/null 2>&1; then \
				break; \
			fi; \
			i=$$((i + 1)); \
			sleep 1; \
		done; \
		if ! curl -fsS "http://$(HOST):$(UI_PORT)/agents/search" >/dev/null 2>&1; then \
			echo "UI did not become ready; see $$UI_LOG_PATH"; \
			exit 1; \
		fi; \
	fi; \
	curl -fsS "http://$(HOST):$(UI_PORT)/agents/search" >/dev/null 2>&1 || true; \
		cd $(UI_DIR) && UI_PORT=$(UI_PORT) PLAYWRIGHT_REUSE_EXISTING_SERVER=1 RUN_REAL_BACKEND_E2E=1 PY_AG_UI_URL=http://$(HOST):$(PORT)/ag-ui/ E2E_SMOKE_ASSISTANT_TEXT="$(SMOKE_ASSISTANT_TEXT)" pnpm playwright test --config playwright.real.config.ts --grep "sends and receives messages via CopilotKit UI"

dev: dev-human

human: dev-human

# Human-only convenience entrypoint in the canonical checkout.
dev-human:
	@HUMAN_DEV_SLOT="$(HUMAN_DEV_SLOT)" ./scripts/human_dev.sh

dev-all: guard-full-bootstrap
	@set -e; \
	trap 'kill 0' INT TERM EXIT; \
	$(MAKE) chat & \
	sleep 2; \
	$(MAKE) ui-dev-real & \
	wait

dev-all-mock: guard-full-bootstrap
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

agent-start-docs:
	@if [ -n "$(ISSUE)" ]; then \
		./scripts/worktree/start-task.sh --issue "$(ISSUE)" --mode docs; \
	elif [ -n "$(QUERY)" ]; then \
		./scripts/worktree/start-task.sh --query "$(QUERY)" --mode docs; \
	else \
		echo "Usage: make agent-start-docs ISSUE=<id> OR QUERY=\"text\""; \
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
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) pyrefly check
	$(MAKE) ui-lint
	$(MAKE) ui-typecheck
	$(MAKE) coverage
