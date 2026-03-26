# Deployment Environment Bootstrap

This runbook covers the one-off environment bootstrap path for the deployed
`dev` environment.

Normal release deploys do not run this flow.
They only verify that the seed state created by this flow is already ready.

## Why This Exists

The deployed Aurora writer is private to the VPC.
That means the seed step cannot run directly from Tal's laptop or a
GitHub-hosted runner against the database endpoint.

The bootstrap flow therefore splits into two parts:

1. use Tal's canonical checkout to stage the pinned parquet and image-catalog
   inputs plus the immutable `images/masters/` objects
2. run the actual seed step as a one-off backend ECS task inside the VPC

This keeps environment bootstrap explicit and repeatable without putting
repo-local data requirements into every application deploy.

## Current Inputs

The current `dev` bootstrap contract uses these repository variables:

- `PRODUCT_IMAGE_BUCKET_NAME`
- `PRIVATE_ARTIFACTS_BUCKET_NAME`
- `ECS_CLUSTER_NAME`
- `ECS_BACKEND_TASK_DEFINITION_FAMILY`
- `ECS_RUN_TASK_SUBNET_IDS_JSON`
- `ECS_BACKEND_RUN_TASK_SECURITY_GROUP_IDS_JSON`
- `IKEA_IMAGE_CATALOG_RUN_ID`

As of 2026-03-26, `IKEA_IMAGE_CATALOG_RUN_ID` is
`germany-all-products-20260318`.

## Command

From any checkout that has the bootstrap code, while pointing at Tal's
canonical data checkout when needed:

```bash
export AWS_DEFAULT_PROFILE=tal
export AWS_REGION=eu-central-1

make deploy-bootstrap-environment \
  PRODUCT_IMAGE_BUCKET_NAME="$(gh variable get PRODUCT_IMAGE_BUCKET_NAME)" \
  PRIVATE_ARTIFACTS_BUCKET_NAME="$(gh variable get PRIVATE_ARTIFACTS_BUCKET_NAME)" \
  ECS_CLUSTER_NAME="$(gh variable get ECS_CLUSTER_NAME)" \
  ECS_BACKEND_TASK_DEFINITION_FAMILY="$(gh variable get ECS_BACKEND_TASK_DEFINITION_FAMILY)" \
  ECS_RUN_TASK_SUBNET_IDS_JSON="$(gh variable get ECS_RUN_TASK_SUBNET_IDS_JSON)" \
  ECS_BACKEND_RUN_TASK_SECURITY_GROUP_IDS_JSON="$(gh variable get ECS_BACKEND_RUN_TASK_SECURITY_GROUP_IDS_JSON)" \
  IKEA_IMAGE_CATALOG_RUN_ID="$(gh variable get IKEA_IMAGE_CATALOG_RUN_ID)" \
  BOOTSTRAP_INPUT_REPO_ROOT=/Users/tal/dev/tal_maria_ikea
```

Optional:

- append `FORCE=1` only when you intentionally want to reseed even if the same
  versions are already recorded in `ops.seed_state`
- override `BOOTSTRAP_RUN_TASK_CPU` or `BOOTSTRAP_RUN_TASK_MEMORY` if the
  one-off seed task needs more room than the steady-state backend service

## What The Script Does

`scripts/deploy/bootstrap_environment.sh` performs these steps:

1. reads the pinned parquet and image-catalog versions from the canonical
   bootstrap-input checkout plus the shared image-catalog root
2. syncs `images/masters/` into the product-image bucket under `masters/`
3. uploads the current parquet inputs, preserving the dataset-directory shape,
   plus the selected image-catalog artifact into the private artifacts bucket
   under a unique `bootstrap/...` prefix
4. starts one backend ECS task with
   `python -m scripts.deploy.bootstrap_catalog_from_s3 ...`
5. starts one second backend ECS task with
   `python -m scripts.deploy.verify_seed_state ...`

The ECS tasks use the deployed backend task role and private-network access, so
they can reach Aurora without opening the database to laptops or CI runners.
They also use explicit task-level CPU and memory overrides so the one-off seed
job can be sized independently from the always-on backend service.

## Validation

Useful validation for the current environment is:

- `curl https://designagent.talperry.com/api/health`
- `curl https://designagent.talperry.com/api/agents`
- `curl -I https://designagent.talperry.com/static/product-images/masters/<known-key>`

The backend readiness payload should report:

- `database.status = ok`
- `schema.status = ok`
- `seed_state.status = ok`
- `catalog_data.status = ok`
