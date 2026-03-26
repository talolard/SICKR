# Deployment Runtime Contract

Read [guiding_principles.md](../specs/deploy/guiding_principles.md) first.
Read [00_context.md](../specs/deploy/subspecs/00_context.md) for the shared
deployment assumptions.

The files under `specs/deploy/` are the current source of truth for deployment
work and trump older deployment notes and plans. Older deploy plans that still
assume EC2, SSM, host deploy bundles, or manual ECS backstops are historical
background only. This document exists to make the deploy-time runtime contract
explicit for implementers and CI.

## Purpose

This project now deploys the application runtime as:

- one `backend` ECS Fargate task definition and service
- one `ui` ECS Fargate task definition and service
- one ALB that routes `/ag-ui/*`, `/api/agents*`, and `/api/health*` to
  `backend`, and everything else to `ui`
- one CloudFront distribution in front of that ALB and the product-image bucket

This contract keeps one important distinction explicit:

- **environment bootstrap** is one-off work that populates database state and
  image metadata
- **application deploy** rolls out new `ui` and `backend` images onto ECS

Normal application deploys do not require repo-local image catalogs, host-local
state, or a machine-oriented deploy bundle.

## Rules

- never bake long-lived secrets into images
- keep non-secret runtime config in ECS task-definition environment values
- keep secrets in AWS Secrets Manager and inject them through ECS task
  definition `secrets`
- prefer canonical variable names even where the application still accepts
  older aliases for compatibility
- let Terraform own the stable task-definition baseline and let CI own
  task-definition revisions and service rollouts

## Secrets Manager Contract

Terraform creates these secret containers:

- `tal-maria-ikea/dev/backend-app`
- `tal-maria-ikea/dev/model-providers`
- `tal-maria-ikea/dev/observability`
- `tal-maria-ikea/dev/database`

Expected key usage inside those secrets:

| Secret | Expected keys | Notes |
| --- | --- | --- |
| `backend-app` | reserved for backend-only sensitive values | keep stable even if v1 leaves it empty |
| `model-providers` | `GEMINI_API_KEY`, `FAL_KEY` | use canonical names in deployed env |
| `observability` | `LOGFIRE_TOKEN` | optional for remote Logfire export |
| `database` | `DATABASE_URL` | one DSN for the Aurora writer endpoint |

Deploy automation should not read individual secret values in CI. Instead:

- Terraform wires the secret ARNs into the ECS task definitions
- ECS resolves the secret keys into environment variables at task start

## Backend Task Contract

The backend ECS task definition should carry these non-secret values directly:

| Variable | Required value for current deploy | Why |
| --- | --- | --- |
| `APP_ENV` | `dev` | matches the current single deployment environment root |
| `LOG_LEVEL` | `INFO` | conservative default for low-volume public use |
| `LOG_JSON` | `true` | keeps logs structured for Logfire and later collection |
| `LOGFIRE_SERVICE_NAME` | `ikea-agent` | stable service identity |
| `LOGFIRE_SERVICE_VERSION` | release version, patched by CI | ties telemetry to the rolled-out revision |
| `LOGFIRE_ENVIRONMENT` | `dev` | explicit environment labeling for traces and logs |
| `LOGFIRE_SEND_MODE` | `if-token-present` | deploy works without a token but exports when configured |
| `DATABASE_POOL_MODE` | `nullpool` | deploy-friendly connection policy for Aurora pause-to-zero |
| `ALLOW_MODEL_REQUESTS` | `1` | the deployed app should use the real model path |
| `IMAGE_SERVING_STRATEGY` | `direct_public_url` | public launch requires bucket-backed image delivery |
| `IMAGE_SERVICE_BASE_URL` | `https://designagent.talperry.com/static/product-images` | stable same-host image base for runtime payloads |
| `ARTIFACT_ROOT_DIR` | `/var/lib/ikea-agent/artifacts` | writable in-container materialization/cache root |
| `ARTIFACT_STORAGE_BACKEND` | `s3` | durable private artifacts live outside container-local disk |
| `ARTIFACT_S3_BUCKET` | deploy-specific private bucket name | durable private storage bucket |
| `ARTIFACT_S3_PREFIX` | `dev` | optional bucket-relative root for private object keys |
| `ARTIFACT_S3_REGION` | `eu-central-1` | explicit region when runtime should not rely on ambient config |
| `FEEDBACK_CAPTURE_ENABLED` | `0` | keep optional local capture disabled in deployed v1 |
| `TRACE_CAPTURE_ENABLED` | `0` | keep local trace-bundle capture disabled in deployed v1 |

The backend task should receive these secret-backed values from ECS secret
injection:

- `DATABASE_URL`
- `GEMINI_API_KEY`
- `FAL_KEY`
- `LOGFIRE_TOKEN` when observability export is enabled

Product-image note:

- when `IMAGE_SERVICE_BASE_URL` is set, catalog seeding should write same-host
  public URLs of the form
  `https://designagent.talperry.com/static/product-images/masters/<image-asset-key>`
  into `catalog.product_images.public_url`

## UI Task Contract

The UI ECS task definition should remain secret-free and should carry:

| Variable | Required value for current deploy | Why |
| --- | --- | --- |
| `NODE_ENV` | `production` | production Next.js behavior |
| `APP_ENV` | `dev` | release/environment tag for server-side UI logs |
| `APP_RELEASE_VERSION` | release version, patched by CI | release tag for server-side UI logs |
| `PY_AG_UI_URL` | `http://<alb-dns>/ag-ui/` | CopilotKit and AG-UI client traffic target the public AG-UI listener path |
| `BACKEND_PROXY_BASE_URL` | `http://<alb-dns>/` | server-side UI proxy origin for residual backend-owned routes such as `/api/rooms/*` and `/attachments*`, resolved through normal ALB path rules |
| `NEXT_PUBLIC_USE_MOCK_AGENT` | `0` | deployed UI must use the real backend |
| `NEXT_PUBLIC_TRACE_CAPTURE_ENABLED` | `0` | keep trace capture off unless explicitly enabled later |

No browser-visible secrets belong in the UI runtime contract.

## ECS Baseline Contract

Terraform should own the stable ECS baseline:

- ECS cluster name
- ALB and target groups
- task-definition families
- task execution and task roles
- secret ARNs wired into task definitions
- CloudWatch log groups
- initial services with `desired_count = 0` and placeholder task definitions

The CI deploy workflow should then:

1. build and push immutable image digests
2. write the release manifest
3. describe the current ECS task definitions
4. render new task-definition revisions by replacing the image and release
   version fields
5. strip any placeholder bootstrap command such as `sleep infinity` from the
   rendered task definition so ECS uses the image-default runtime command
6. run one-off backend migration and seed-verification tasks on Fargate
7. update the backend service to the new task definition and wait until that
   exact revision is the only active backend deployment serving the full
   service desired count
8. update the UI service to the new task definition

This keeps the stable runtime contract in Terraform while keeping release
rollouts source-controlled and repeatable.

Current implementation note:

- the repo already exports the needed cluster/service names and ALB DNS through
  Terraform outputs
- the current workflows still describe ECS services and the ALB live to derive
  some rollout inputs
- that discovery is transitional implementation debt, not the intended contract

## Deploy Inputs

The ECS deploy workflow should work from these inputs:

| Input | Source |
| --- | --- |
| `AWS_REGION` | fixed deploy config: `eu-central-1` |
| `ECS_CLUSTER_NAME` | Terraform output / GitHub repo variable |
| `ECS_BACKEND_SERVICE_NAME` | Terraform output / GitHub repo variable |
| `ECS_UI_SERVICE_NAME` | Terraform output / GitHub repo variable |
| `RELEASE_VERSION` | release manifest `app_version` |
| `RELEASE_GIT_TAG` | release manifest `git_tag` |
| `RELEASE_GIT_SHA` | release manifest `git_sha` |
| `BACKEND_IMAGE_REF` | release manifest `backend_image.digest_ref` |
| `UI_IMAGE_REF` | release manifest `ui_image.digest_ref` |
| `POSTGRES_SEED_VERSION` | release manifest `bootstrap.postgres_seed_version` |
| `IMAGE_CATALOG_RUN_ID` | release manifest `bootstrap.image_catalog_run_id` |

Old EC2 deploy inputs such as host ports, deploy-state directories, SSM
payloads, and Compose project names are intentionally out of contract now.

## Rollback Contract

There is no special host-side rollback state anymore.

Rollback should mean:

- select an older immutable Git release tag
- read its release manifest
- render ECS task-definition revisions from the current baseline with the older
  digest refs
- redeploy those services through the same ECS workflow

That is simpler and more transparent than maintaining host-local “previous
release” files.

## Validation Expectations

Useful validation for this contract includes:

- local tests for manifest parsing and ECS task-definition rendering
- `terraform validate` for the Fargate/ALB runtime surface
- CI dry runs or real workflow validation for task-definition registration
- one real Fargate migration task run before the first public launch
- one migration-task validation that fails if Alembic reports head while any
  required `app.*` runtime table is still missing
- one real public-path validation on `designagent.talperry.com` after the ECS
  services are live, including `/api/agents` and
  `/api/agents/{agent}/metadata`
- one validation that percent-encoded database credentials survive the Alembic
  migration config path unchanged
