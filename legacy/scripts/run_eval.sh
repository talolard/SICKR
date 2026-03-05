#!/usr/bin/env bash
set -euo pipefail

INDEX_RUN_ID="${1:-latest}"
K_VALUE="${2:-10}"

uv run python -m ikea_agent.eval.run --index-run-id "${INDEX_RUN_ID}" --k "${K_VALUE}"
