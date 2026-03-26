# Deployment Bootstrap Validation 2026-03-26

This note records the live evidence used to close the remaining blockers for
`tal_maria_ikea-v9b.5.7`:

- `tal_maria_ikea-v9b.3.4`
- `tal_maria_ikea-v9b.4.3`
- `tal_maria_ikea-v9b.4.6`

## Why This Validation Was Needed

The code changes for deploy and bootstrap were already locally validated, but
those blockers were specifically about whether the deployed environment and the
runtime contract were real:

- `3.4` needed a repeatable one-off bootstrap path that does not depend on a
  laptop having direct Aurora access.
- `4.3` needed proof that the live ALB, ECS, and public app origin substrate
  exist and are serving the intended routes.
- `4.6` needed proof that deploy and bootstrap inputs can come from Terraform
  outputs and repo configuration rather than fresh live discovery.

## Live Environment Facts

Validated in AWS account `046673074482`, region `eu-central-1`, using profile
`tal`.

- ECS cluster: `ikea-agent-dev-cluster`
- Backend service: `ikea-agent-dev-backend`
- UI service: `ikea-agent-dev-ui`
- Public hostname: `designagent.talperry.com`
- Product image bucket: `ikea-agent-dev-046673074482-product-images`
- Private artifacts bucket: `ikea-agent-dev-046673074482-private-artifacts`

The live public path and runtime foundation are active:

- `https://designagent.talperry.com/api/health`
- `https://designagent.talperry.com/api/agents`
- `https://designagent.talperry.com/static/product-images/masters/...`

## Bootstrap Contract Proved

The bootstrap flow now works as an explicit operator path:

1. read pinned parquet and image-catalog inputs from the canonical checkout
2. sync immutable `images/masters/` objects to the product-image bucket
3. upload pinned seed artifacts to the private artifacts bucket under a unique
   `bootstrap/...` prefix
4. run `scripts.deploy.bootstrap_catalog_from_s3` as a one-off ECS task inside
   the VPC
5. run `scripts.deploy.verify_seed_state` as a second one-off ECS task

This matters because Tal's laptop cannot directly reach the private Aurora
writer endpoint, so the actual seed step has to happen inside ECS.

## Runtime Issues Found During Validation

The live validation exposed two real issues that were fixed in this branch:

1. The deployed backend image on ECS did not yet contain
   `scripts.deploy.bootstrap_catalog_from_s3`.
   To prove the runtime path without waiting on merges, a temporary backend
   image was built and pushed:
   `046673074482.dkr.ecr.eu-central-1.amazonaws.com/ikea-agent/backend:manual-bootstrap-20260326-6091895`

2. The one-off bootstrap task was OOM-killed at the steady-state backend task
   size (`1024` MiB).
   The operator path now uses explicit task-level overrides so bootstrap can be
   sized independently from the always-on backend service.

The successful validation run used:

- task definition family: `ikea-agent-dev-backend`
- active temporary revision for bootstrap proof: `ikea-agent-dev-backend:11`
- task override CPU: `1024`
- task override memory: `4096`

## Final Observed State

After the successful bootstrap and seed verification run, the public health
endpoint reported:

- overall status: `ok`
- database: `ok`
- schema: `ok`
- seed_state: `ok`
- catalog_data: `ok`
- missing public image URLs: `0`
- image serving strategy: `direct_public_url`

Observed seeded versions:

- `postgres_catalog`:
  `43c529a4ccc987ba28fde049d190a3d11bcc37e56c169d8d6ce722ffe5b2db64`
- `image_catalog`:
  `3a6c13216416e6c8d27767905814e5c50613c0382033ff2b845d39f2666bb6bd`

Observed table counts:

- `catalog.products_canonical = 10300`
- `catalog.product_embeddings = 10300`
- `catalog.product_images = 46279`

These values match the current repo-side bootstrap inputs for:

- `data/parquet/products_canonical`
- `data/parquet/product_embeddings`
- image catalog run id `germany-all-products-20260318`

## Validation Commands

Useful validation that was actually run:

```bash
bash -n scripts/deploy/bootstrap_environment.sh

env -u VIRTUAL_ENV uv run pytest \
  tests/scripts/deploy/test_bootstrap_catalog_from_s3.py \
  tests/scripts/deploy/test_ecs_release_deploy.py \
  tests/scripts/deploy/test_seed_verification.py \
  tests/scripts/deploy/test_render_ecs_task_definition.py

curl -fsS https://designagent.talperry.com/api/health | jq .
curl -fsS https://designagent.talperry.com/api/agents | jq '.agents | length'
curl -I -fsS \
  https://designagent.talperry.com/static/product-images/masters/abyan-body-puff-set-of-3-orange-green-white__1330617_pe945731_s5.jpg
```

Live AWS checks were also used to inspect ECS tasks, task definitions, CloudWatch
logs, ALB-backed services, S3 objects, and the resulting seed state.

## What This Closes

- `tal_maria_ikea-v9b.3.4` is now satisfied because the one-off environment
  bootstrap path is explicit, repeatable, and proven against the deployed VPC
  runtime.
- `tal_maria_ikea-v9b.4.3` is now satisfied because the live ECS, ALB, and
  public-origin substrate is proven by both AWS inspection and public traffic.
- `tal_maria_ikea-v9b.4.6` is now satisfied because the deploy/bootstrap path
  now uses repo-configured task families, ALB DNS, and run-task network inputs
  instead of deriving those stable inputs from ad hoc live discovery.

## Remaining Operational Note

The temporary backend image and task-definition revision were used only to prove
the new bootstrap runtime before the stacked PRs merge. Once the branch stack is
merged and the normal release publish flow builds a canonical backend image with
this code, that temporary image tag is no longer the intended long-term path.
