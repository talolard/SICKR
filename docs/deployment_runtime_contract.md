# Deployment Runtime Contract

Read [guiding_principles.md](../specs/deploy/guiding_principles.md) first.
Read [00_context.md](../specs/deploy/subspecs/00_context.md) for the shared
deployment assumptions.

The files under `specs/deploy/` are the current source of truth for deployment
work and trump older deployment notes and plans. This document exists to make
the runtime environment contract explicit for implementers and deploy tooling.

## Purpose

This project uses a split runtime:

- one `backend` container
- one `ui` container
- one host-level deploy layer that injects runtime configuration

The contract below is the stable deploy-facing environment surface. The release
workflow, Terraform outputs, and later host deploy automation should all reuse
this contract instead of inventing new environment semantics.

This contract also makes one deployment distinction explicit:

- **environment bootstrap** prepares catalog data and image metadata
- **application deploy** rolls out new `ui` and `backend` images

Normal application deploys do not require repo-local image-catalog files on the
host.

## Rules

- never bake long-lived secrets into images
- keep non-secret runtime config in plain env files or explicit deploy config
- keep secrets in AWS Secrets Manager and map secret keys to environment
  variables at container start
- prefer canonical variable names even where the application still accepts older
  aliases for compatibility

## Secrets Manager Contract

Terraform creates these secret containers:

- `tal-maria-ikea/dev/backend-app`
- `tal-maria-ikea/dev/model-providers`
- `tal-maria-ikea/dev/observability`
- `tal-maria-ikea/dev/database`

Expected key usage inside those secrets:

| Secret | Expected keys | Notes |
| --- | --- | --- |
| `backend-app` | reserved for backend-only sensitive values | create now so later deploy automation has a stable ARN even if v1 leaves it empty |
| `model-providers` | `GEMINI_API_KEY`, `FAL_KEY` | use canonical names; do not prefer `GOOGLE_API_KEY` or `FAI_AI_API_KEY` in deployed env |
| `observability` | `LOGFIRE_TOKEN` | optional for remote Logfire export |
| `database` | `DATABASE_URL` | one DSN for the Aurora writer endpoint |

Deploy tooling should project secret JSON keys into container environment
variables with the same names.

## Backend Contract

The backend container should receive these non-secret values directly from the
host deploy layer:

| Variable | Required value for current deploy | Why |
| --- | --- | --- |
| `APP_ENV` | `dev` | matches the current single deployment environment root |
| `LOG_LEVEL` | `INFO` | conservative default for low-volume public use |
| `LOG_JSON` | `true` | keeps logs structured for Logfire and later collection |
| `LOGFIRE_SERVICE_NAME` | `ikea-agent` | stable service identity |
| `LOGFIRE_ENVIRONMENT` | `dev` | explicit environment labeling for traces and logs |
| `LOGFIRE_SERVICE_VERSION` | release version, for example `0.1.0` | ties telemetry to the published release |
| `LOGFIRE_SEND_MODE` | `if-token-present` | deploy works without a token but exports when configured |
| `DATABASE_POOL_MODE` | `nullpool` | deploy-friendly connection policy for Aurora pause-to-zero |
| `ALLOW_MODEL_REQUESTS` | `1` | the deployed app should use the real model path |
| `IMAGE_SERVING_STRATEGY` | `direct_public_url` | public launch requires bucket-backed image delivery |
| `IMAGE_SERVICE_BASE_URL` | `https://designagent.talperry.com/static/product-images` | stable same-origin image base for runtime payloads |
| `ARTIFACT_ROOT_DIR` | `/var/lib/ikea-agent/artifacts` | mounted writable path for local materialization and read cache |
| `ARTIFACT_STORAGE_BACKEND` | `s3` | deployed private artifacts must not rely on container-local disk as the durable store |
| `ARTIFACT_S3_BUCKET` | deploy-specific private bucket name | durable private storage bucket for uploads and generated artifacts |
| `ARTIFACT_S3_PREFIX` | `dev` or other environment prefix | optional bucket-relative root for private object keys |
| `ARTIFACT_S3_REGION` | `eu-central-1` | explicit region when the runtime should not rely on ambient AWS config |
| `FEEDBACK_CAPTURE_ENABLED` | `0` | keep optional local capture disabled in deployed v1 |
| `TRACE_CAPTURE_ENABLED` | `0` | keep local trace-bundle capture disabled in deployed v1 |

The backend container should receive these secret-backed values from Secrets
Manager:

- `DATABASE_URL`
- `GEMINI_API_KEY`
- `FAL_KEY`
- `LOGFIRE_TOKEN` when observability export is enabled

Product-image note:

- when `IMAGE_SERVICE_BASE_URL` is set, catalog seeding should write same-host
  public URLs of the form
  `https://designagent.talperry.com/static/product-images/masters/<image-asset-key>`
  into `catalog.product_images.public_url`

## UI Contract

The UI container should receive only non-secret runtime values:

| Variable | Required value for current deploy | Why |
| --- | --- | --- |
| `NODE_ENV` | `production` | production Next.js behavior |
| `APP_ENV` | `dev` | release/environment tag for server-side UI logs |
| `APP_RELEASE_VERSION` | release version, for example `0.1.0` | release tag for server-side UI logs |
| `PY_AG_UI_URL` | `http://backend:8000/ag-ui/` | server-side UI routes call the backend over the internal container network |
| `NEXT_PUBLIC_USE_MOCK_AGENT` | `0` | deployed UI must use the real backend |
| `NEXT_PUBLIC_TRACE_CAPTURE_ENABLED` | `0` | keep trace capture off unless explicitly enabled later |

No browser-visible secrets belong in the UI runtime contract.

## Host And Deploy Contract

The host deploy layer should work from these inputs:

| Variable | Source |
| --- | --- |
| `AWS_REGION` | fixed deploy config: `eu-central-1` |
| `COMPOSE_PROJECT_NAME` | fixed deploy config: `ikea-agent-dev` |
| `BACKEND_IMAGE_REF` | release manifest `backend_image.digest_ref` |
| `UI_IMAGE_REF` | release manifest `ui_image.digest_ref` |
| `RELEASE_VERSION` | release manifest `app_version` |
| `RELEASE_GIT_TAG` | release manifest `git_tag` |
| `RELEASE_GIT_SHA` | release manifest `git_sha` |
| `BACKEND_APP_SECRET_ARN` | Terraform output |
| `MODEL_PROVIDER_SECRET_ARN` | Terraform output |
| `OBSERVABILITY_SECRET_ARN` | Terraform output |
| `DATABASE_SECRET_ARN` | Terraform output |
| `PRODUCT_IMAGE_BASE_URL` | fixed deploy config: `https://designagent.talperry.com/static/product-images` |
| `BACKEND_HOST_PORT` | fixed deploy config: `8000` |
| `UI_HOST_PORT` | fixed deploy config: `3000` |
| `DEPLOY_STATE_DIR` | fixed deploy config: `/var/lib/ikea-agent/deploy` |
| `BACKEND_SECRETS_ENV_FILE` | fixed deploy config: `/var/lib/ikea-agent/deploy/runtime/backend.secrets.env` |
| `HOST_ARTIFACT_ROOT_DIR` | fixed deploy config: `/var/lib/ikea-agent/artifacts` |

The host should mount one writable path for backend artifact materialization and
cache:

- `/var/lib/ikea-agent/artifacts`

The host should also keep one deploy-state root:

- `/var/lib/ikea-agent/deploy`

That deploy-state root stores:

- extracted release bundles under `releases/<git_tag>/`
- one non-versioned backend secret env file under `runtime/backend.secrets.env`
- the current deployed release tag
- the previous deployed release tag
- current and previous manifest snapshots for rollback bookkeeping

The deploy runner should consume release-manifest digests, fetch the required
Secrets Manager values, and inject only the contract above into the containers.
It should not persist secret values in versioned release directories.

## Environment Bootstrap Contract

Environment bootstrap is a separate workflow from normal app deploy.

Its job is to:

- upload immutable product image objects to S3
- seed or refresh `catalog.*` and `ops.seed_state`
- prepare `catalog.product_images.public_url` for `direct_public_url` mode

This workflow may use:

- `uv run python scripts/deploy/bootstrap_catalog.py`
- repo-local parquet inputs
- repo-local image-catalog run outputs

It is not a required step on every release deploy.

## Application Deploy Entry Points

The steady-state deploy contract now exposes these deploy-facing commands:

- `uv run python scripts/deploy/apply_migrations.py`
- `uv run python scripts/deploy/verify_seed_state.py`
- `uv run python scripts/deploy/wait_for_http_ready.py --url <health-url>`
- `uv run python scripts/deploy/prove_agui_streaming.py --url <ag-ui-agent-url>`
  - this validates SSE response framing and first-event delivery only
  - it does not by itself prove unbuffered progressive streaming through the
    full public CloudFront path

Expected health URLs:

- backend liveness: `/api/health/live`
- backend readiness: `/api/health/ready`
- UI liveness: `/api/health/live`
- UI readiness: `/api/health/ready`

`/api/health` remains the compatibility alias for UI readiness.

## Deploy Bundle Contract

The release and deploy workflows now render one deploy bundle before invoking
SSM. That bundle is the host-side execution unit and contains:

- `release-manifest.json`
- `host.env`
- `backend.env`
- `ui.env`
- `docker-compose.yml`
- `scripts/host_bundle_runner.py`
- one pre-rendered `release-deploy-ssm-command.json` payload distributed with
  the release assets

The host runner is responsible for:

1. reading the secret ARNs from `host.env`
2. projecting secret JSON keys into the non-versioned runtime secret env file
3. pulling pinned image digests
4. running migrations
5. running seed verification against the already-prepared environment
6. starting backend, then UI
7. waiting for backend readiness, UI readiness, and one lightweight app check
8. updating current and previous deploy state markers

Rollback uses the previous recorded deploy bundle by exact image digests and
skips schema migration by default, because DB rollback is not assumed safe.
Both deploy and rollback operations are serialized by the workflow concurrency
key and by a host-local deploy lock so two overlapping SSM commands cannot
interleave state changes.

## Example Env Files

These example files document the current expected values:

- `docker/env/backend.env.example`
- `docker/env/ui.env.example`
- `docker/env/host.env.example`
- `docker/compose.deploy.yml`

They are examples, not sources of secret truth.
