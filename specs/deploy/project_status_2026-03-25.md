# Deployment Project Status

Last updated: 2026-03-25

Read [guiding_principles.md](./guiding_principles.md) first.
The documents under `specs/deploy/` are the current source of truth for this
deployment project and trump older deployment plans, notes, and critiques.

## Current Canonical Direction

The deployment project has pivoted from:

- `CloudFront + EC2 host + SSM + docker compose`

to:

- `CloudFront + ALB + ECS Fargate + Aurora + S3`

This is an intentional simplification move. The trade is:

- higher steady-state app runtime cost
- much lower host-management burden

For this project, that is the right trade.

## What Is Implemented In The Repo Now

The repo now contains:

- production `ui` and `backend` Dockerfiles
- release-manifest generation
- release-please-driven image publication
- migration stairway validation in PR CI and release validation
- ECS-oriented deploy workflows
- an ECS task-definition renderer
- Terraform modules for:
  - network
  - database
  - storage
  - edge
  - runtime
- a rewritten deploy spec set that treats Fargate+ALB as canonical

The old EC2-host deploy path has been removed from the repo surface:

- no host deploy bundle renderer
- no host-bundle runner
- no SSM command payload writer
- no production `docker compose` deploy file
- no host deploy env example
- no EC2 compute module

## What This Makes Redundant

The following work should now be treated as obsolete, not as an alternate path:

- provisioning or debugging the single EC2 app host
- origin-host DNS for the app runtime
- SSM-based deploy workflows
- host-local rollback bookkeeping
- host-local compose orchestration
- any design that still assumes `nginx` or a host reverse proxy is required

## Major Gaps Still Open

The pivot is real, but it does not mean the deployment is done.

The biggest remaining gaps are:

1. The new Terraform runtime still needs real `plan` and likely iterative fixes.
2. The GitHub repo variables need to shift from EC2-targeting values to ECS
   values:
   - `ECS_CLUSTER_NAME`
   - `ECS_BACKEND_SERVICE_NAME`
   - `ECS_UI_SERVICE_NAME`
3. The first environment bootstrap still has to happen against the target
   Aurora cluster.
4. Product images still need to be present in the public bucket before launch.
5. We still need one real end-to-end proof of:
   - AG-UI streaming through `CloudFront -> ALB -> backend`
   - Aurora pause-to-zero under the deployed runtime posture
6. The new release/deploy hardening lane still needs the rest of epic `.8`
   closed out so the next release does not depend on manual recovery.

## Work We Need To Do Before First Real Deploy

Before the first real ECS deploy can succeed, we still need:

1. `terraform validate`
2. a real Terraform apply for the Fargate/ALB runtime
3. GitHub repo variables updated from Terraform outputs
4. one release publish run to push immutable images
5. one one-off bootstrap run for the target environment
6. one deploy workflow run against ECS

## Epic Impact

This architecture pivot changes the meaning of several epics and tasks.

Most importantly:

- Terraform/AWS work now means ECS+ALB runtime, not EC2 host bring-up
- build/publish/deploy automation now means ECS task-definition and service
  rollout, not SSM host orchestration
- launch-readiness validation must prove the public ECS path, not an EC2 host
- the Beads graph has been updated so the runtime, edge, and deploy tasks now
  point at the ECS/ALB substrate rather than the obsolete host path

## Recommended Next Sequence

1. Finish and validate the Terraform Fargate/ALB runtime shape.
2. Populate the new ECS GitHub repo variables from Terraform outputs.
3. Run one first release publication to produce immutable image digests and a
   release manifest.
4. Bootstrap the environment once.
5. Run the first ECS deploy and public-path validation.
