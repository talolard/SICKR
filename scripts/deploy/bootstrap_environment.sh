#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Bootstrap the deployed catalog and product-image metadata through one ECS task.

Usage:
  scripts/deploy/bootstrap_environment.sh \
    --product-image-bucket <bucket> \
    --private-artifacts-bucket <bucket> \
    --ecs-cluster <cluster> \
    --backend-task-definition-family <family> \
    --run-task-subnets-json <json> \
    --run-task-security-groups-json <json> \
    --image-catalog-run-id <run-id> \
    [--run-task-cpu <units>] \
    [--run-task-memory <MiB>] \
    [--bootstrap-input-repo-root <path>] \
    [--public-app-base-url <url>] \
    [--image-catalog-root <path>] \
    [--aws-region <region>] \
    [--force]
USAGE
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "${cmd}" >&2
    exit 1
  fi
}

PRODUCT_IMAGE_BUCKET=""
PRIVATE_ARTIFACTS_BUCKET=""
ECS_CLUSTER_NAME=""
BACKEND_TASK_DEFINITION_FAMILY=""
RUN_TASK_SUBNETS_JSON=""
RUN_TASK_SECURITY_GROUPS_JSON=""
IMAGE_CATALOG_RUN_ID=""
BOOTSTRAP_INPUT_REPO_ROOT=""
RUN_TASK_CPU="1024"
RUN_TASK_MEMORY="4096"
PUBLIC_APP_BASE_URL="https://designagent.talperry.com"
IMAGE_CATALOG_ROOT="/Users/tal/dev/tal_maria_ikea/.tmp_untracked/ikea_image_catalog"
AWS_REGION="${AWS_REGION:-eu-central-1}"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --product-image-bucket)
      PRODUCT_IMAGE_BUCKET="$2"
      shift 2
      ;;
    --private-artifacts-bucket)
      PRIVATE_ARTIFACTS_BUCKET="$2"
      shift 2
      ;;
    --ecs-cluster)
      ECS_CLUSTER_NAME="$2"
      shift 2
      ;;
    --backend-task-definition-family)
      BACKEND_TASK_DEFINITION_FAMILY="$2"
      shift 2
      ;;
    --run-task-subnets-json)
      RUN_TASK_SUBNETS_JSON="$2"
      shift 2
      ;;
    --run-task-security-groups-json)
      RUN_TASK_SECURITY_GROUPS_JSON="$2"
      shift 2
      ;;
    --image-catalog-run-id)
      IMAGE_CATALOG_RUN_ID="$2"
      shift 2
      ;;
    --run-task-cpu)
      RUN_TASK_CPU="$2"
      shift 2
      ;;
    --run-task-memory)
      RUN_TASK_MEMORY="$2"
      shift 2
      ;;
    --bootstrap-input-repo-root)
      BOOTSTRAP_INPUT_REPO_ROOT="$2"
      shift 2
      ;;
    --public-app-base-url)
      PUBLIC_APP_BASE_URL="$2"
      shift 2
      ;;
    --image-catalog-root)
      IMAGE_CATALOG_ROOT="$2"
      shift 2
      ;;
    --aws-region)
      AWS_REGION="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${PRODUCT_IMAGE_BUCKET}" || -z "${PRIVATE_ARTIFACTS_BUCKET}" || -z "${ECS_CLUSTER_NAME}" || -z "${BACKEND_TASK_DEFINITION_FAMILY}" || -z "${RUN_TASK_SUBNETS_JSON}" || -z "${RUN_TASK_SECURITY_GROUPS_JSON}" || -z "${IMAGE_CATALOG_RUN_ID}" ]]; then
  usage
  exit 1
fi

require_cmd aws
require_cmd jq
require_cmd uv

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEFAULT_BOOTSTRAP_INPUT_REPO_ROOT="/Users/tal/dev/tal_maria_ikea"
if [[ -z "${BOOTSTRAP_INPUT_REPO_ROOT}" ]]; then
  BOOTSTRAP_INPUT_REPO_ROOT="${REPO_ROOT}"
  if [[ ! -e "${BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/products_canonical" || ! -e "${BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/product_embeddings" ]]; then
    if [[ -e "${DEFAULT_BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/products_canonical" && -e "${DEFAULT_BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/product_embeddings" ]]; then
      BOOTSTRAP_INPUT_REPO_ROOT="${DEFAULT_BOOTSTRAP_INPUT_REPO_ROOT}"
    fi
  fi
fi
BOOTSTRAP_INPUT_REPO_ROOT="$(cd "${BOOTSTRAP_INPUT_REPO_ROOT}" && pwd)"
IMAGE_CATALOG_ROOT="$(cd "${IMAGE_CATALOG_ROOT}" && pwd)"
PRODUCT_IMAGE_BASE_URL="${PUBLIC_APP_BASE_URL%/}/static/product-images"
MASTERS_ROOT="${IMAGE_CATALOG_ROOT}/images/masters"
PRODUCTS_PARQUET_PATH="${BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/products_canonical"
EMBEDDINGS_PARQUET_PATH="${BOOTSTRAP_INPUT_REPO_ROOT}/data/parquet/product_embeddings"

if [[ ! -d "${MASTERS_ROOT}" ]]; then
  printf 'Expected masters directory at %s\n' "${MASTERS_ROOT}" >&2
  exit 1
fi
if [[ ! -e "${PRODUCTS_PARQUET_PATH}" || ! -e "${EMBEDDINGS_PARQUET_PATH}" ]]; then
  printf 'Expected parquet inputs under %s/data/parquet\n' "${BOOTSTRAP_INPUT_REPO_ROOT}" >&2
  exit 1
fi

BOOTSTRAP_INPUTS_JSON="$(
  env -u VIRTUAL_ENV uv run python -m scripts.deploy.read_bootstrap_inputs \
    --repo-root "${BOOTSTRAP_INPUT_REPO_ROOT}" \
    --image-catalog-run-id "${IMAGE_CATALOG_RUN_ID}"
)"
POSTGRES_SEED_VERSION="$(printf '%s' "${BOOTSTRAP_INPUTS_JSON}" | jq -r '.postgres_seed_version')"
IMAGE_CATALOG_INFO_JSON="$(
  env -u VIRTUAL_ENV uv run python - <<'PY' "${IMAGE_CATALOG_ROOT}" "${IMAGE_CATALOG_RUN_ID}"
from pathlib import Path
import json
import sys

from scripts.deploy.seed_fingerprint import calculate_image_catalog_seed_version
from scripts.docker_deps.seed_postgres import _select_image_catalog_source

image_catalog_root = Path(sys.argv[1]).resolve()
run_id = sys.argv[2]
source = _select_image_catalog_source(image_catalog_root=image_catalog_root, run_id=run_id)
print(
    json.dumps(
        {
            "path": str(source),
            "name": source.name,
            "version": calculate_image_catalog_seed_version(
                image_catalog_root=image_catalog_root,
                image_catalog_source=source,
            ),
        },
        sort_keys=True,
    )
)
PY
)"
IMAGE_CATALOG_SOURCE_PATH="$(printf '%s' "${IMAGE_CATALOG_INFO_JSON}" | jq -r '.path')"
IMAGE_CATALOG_OBJECT_NAME="$(printf '%s' "${IMAGE_CATALOG_INFO_JSON}" | jq -r '.name')"
IMAGE_CATALOG_SEED_VERSION="$(printf '%s' "${IMAGE_CATALOG_INFO_JSON}" | jq -r '.version')"

ARTIFACT_PREFIX="bootstrap/${IMAGE_CATALOG_RUN_ID}/$(date -u +%Y%m%dT%H%M%SZ)"
RUN_TASK_NETWORK_CONFIGURATION="$(
  env -u VIRTUAL_ENV uv run python - <<'PY' "${RUN_TASK_SUBNETS_JSON}" "${RUN_TASK_SECURITY_GROUPS_JSON}"
import json
import sys

subnets = json.loads(sys.argv[1])
security_groups = json.loads(sys.argv[2])
print(
    json.dumps(
        {
            "awsvpcConfiguration": {
                "subnets": subnets,
                "securityGroups": security_groups,
                "assignPublicIp": "ENABLED",
            }
        },
        separators=(",", ":"),
    )
)
PY
)"

upload_s3_path() {
  local source_path="$1"
  local destination_uri="$2"
  if [[ -d "${source_path}" ]]; then
    aws s3 sync \
      "${source_path}/" \
      "${destination_uri%/}/" \
      --region "${AWS_REGION}" \
      --no-progress
  else
    aws s3 cp \
      "${source_path}" \
      "${destination_uri}" \
      --region "${AWS_REGION}" \
      --no-progress
  fi
}

aws s3 sync \
  "${MASTERS_ROOT}/" \
  "s3://${PRODUCT_IMAGE_BUCKET}/masters/" \
  --region "${AWS_REGION}" \
  --no-progress \
  --cache-control "public,max-age=31536000,immutable"

upload_s3_path \
  "${PRODUCTS_PARQUET_PATH}" \
  "s3://${PRIVATE_ARTIFACTS_BUCKET}/${ARTIFACT_PREFIX}/products_canonical"
upload_s3_path \
  "${EMBEDDINGS_PARQUET_PATH}" \
  "s3://${PRIVATE_ARTIFACTS_BUCKET}/${ARTIFACT_PREFIX}/product_embeddings"
upload_s3_path \
  "${IMAGE_CATALOG_SOURCE_PATH}" \
  "s3://${PRIVATE_ARTIFACTS_BUCKET}/${ARTIFACT_PREFIX}/${IMAGE_CATALOG_OBJECT_NAME}"

run_backend_task() {
  local overrides_json
  local task_arn
  local task_payload
  overrides_json="$(
    env -u VIRTUAL_ENV uv run python - <<'PY' "${RUN_TASK_CPU}" "${RUN_TASK_MEMORY}" "$@"
import json
import sys

task_cpu = sys.argv[1]
task_memory = sys.argv[2]
print(
    json.dumps(
        {
            "cpu": task_cpu,
            "memory": task_memory,
            "containerOverrides": [
                {
                    "name": "backend",
                    "command": sys.argv[3:],
                }
            ]
        },
        separators=(",", ":"),
    )
)
PY
  )"
  task_payload="$(
    aws ecs run-task \
      --cluster "${ECS_CLUSTER_NAME}" \
      --launch-type FARGATE \
      --task-definition "${BACKEND_TASK_DEFINITION_FAMILY}" \
      --network-configuration "${RUN_TASK_NETWORK_CONFIGURATION}" \
      --overrides "${overrides_json}" \
      --region "${AWS_REGION}" \
      --output json
  )"
  task_arn="$(printf '%s' "${task_payload}" | jq -r '.tasks[0].taskArn // empty')"
  if [[ -z "${task_arn}" ]]; then
    printf 'Failed to start bootstrap ECS task.\nPayload: %s\n' "${task_payload}" >&2
    exit 1
  fi
  aws ecs wait tasks-stopped \
    --cluster "${ECS_CLUSTER_NAME}" \
    --tasks "${task_arn}" \
    --region "${AWS_REGION}"
  task_payload="$(
    aws ecs describe-tasks \
      --cluster "${ECS_CLUSTER_NAME}" \
      --tasks "${task_arn}" \
      --region "${AWS_REGION}" \
      --output json
  )"
  if [[ "$(printf '%s' "${task_payload}" | jq -r '.tasks[0].containers[] | select(.name == "backend") | .exitCode // empty')" != "0" ]]; then
    printf 'Bootstrap ECS task %s failed.\nPayload: %s\n' "${task_arn}" "${task_payload}" >&2
    exit 1
  fi
}

bootstrap_command=(
  python
  -m
  scripts.deploy.bootstrap_catalog_from_s3
  --artifacts-bucket
  "${PRIVATE_ARTIFACTS_BUCKET}"
  --artifacts-prefix
  "${ARTIFACT_PREFIX}"
  --image-catalog-object-name
  "${IMAGE_CATALOG_OBJECT_NAME}"
  --image-catalog-run-id
  "${IMAGE_CATALOG_RUN_ID}"
  --product-image-base-url
  "${PRODUCT_IMAGE_BASE_URL}"
  --aws-region
  "${AWS_REGION}"
)
if (( FORCE == 1 )); then
  bootstrap_command+=(--force)
fi
run_backend_task "${bootstrap_command[@]}"

run_backend_task \
  python \
  -m \
  scripts.deploy.verify_seed_state \
  --expected-postgres-seed-version \
  "${POSTGRES_SEED_VERSION}" \
  --expected-image-catalog-seed-version \
  "${IMAGE_CATALOG_SEED_VERSION}"
