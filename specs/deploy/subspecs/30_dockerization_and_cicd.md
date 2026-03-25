# Dockerization And CI/CD

This subspec covers the deploy-facing container and CI/CD contract for the
near-term deployment.

Read [00_context.md](./00_context.md) first for the shared goals and high-level
deployment decisions.
Read [25_ecs_fargate_alb_runtime.md](./25_ecs_fargate_alb_runtime.md) for the
runtime substrate.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

For this deployment phase, we should build and release exactly two application
images:

- one `ui` image for the Next.js app
- one `backend` image for the FastAPI + AG-UI runtime

Those images should be built in CI, pushed to `ECR`, and deployed to ECS by
exact immutable references.

The deploy contract between CI and infra should be a small release manifest that
names:

- the application release version
- the released Git commit
- the exact `ui` image reference and digest
- the exact `backend` image reference and digest
- the bootstrap metadata pinned to that release

Deploy should not rebuild images on the runtime platform.

## Why This Is Separate

This is a separate decision from Terraform and AWS topology.

The CI/CD system needs a stable artifact contract even if we later change:

- the Terraform module layout
- the exact ALB or ECS service details
- the deploy trigger mechanism

The key point is that downstream infra consumes pinned application artifacts,
not source code and not host-local builds.

## Image Set

Only two deployable application images are in scope now:

- `ui`
- `backend`

Do not introduce extra deployable images yet for:

- reverse proxies
- migration runners
- data-seed jobs
- local developer dependencies

One-off migration and verification work should reuse the backend task
definition with command overrides, not add a third deployable image.

## Dockerization Expectations

The images should be production-oriented, not developer-shell images.

Expected posture:

- use one Dockerfile per deployable service
- use multi-stage builds where that keeps the runtime image smaller and simpler
- install only production runtime dependencies in the final image
- set explicit startup commands inside the image contract
- attach standard OCI labels for source repo, commit, and release version

The images should not bake in mutable runtime state such as:

- production `.env` files
- database snapshots
- seeded attachment data
- product-image files
- local traces or comments

The deployed images should assume:

- database state comes from Aurora
- public product images come from the separate S3 + CloudFront path
- private attachments and generated artifacts live outside container-local disk

The concrete near-term file layout is:

- `docker/backend.Dockerfile`
- `docker/ui.Dockerfile`
- `docker/env/backend.env.example`
- `docker/env/ui.env.example`
- `scripts/deploy/read_release_version.py`
- `scripts/deploy/write_release_manifest.py`
- `scripts/deploy/render_ecs_task_definition.py`
- `docs/deployment_runtime_contract.md`

The current build posture intentionally targets `linux/amd64` for release
publication because the dependency set still requires it.

## Registry Contract

`ECR` is the target registry for both images.

Recommended repo shape:

- one ECR repo for `ui`, named `ikea-agent/ui`
- one ECR repo for `backend`, named `ikea-agent/backend`

Tagging posture:

- every release gets one app-level `release-please` version
- both images are published under the exact immutable release tag `vX.Y.Z`
- both images should also carry the exact released commit SHA as a secondary
  immutable tag
- no floating tags such as `latest`, `main`, or `release` should be published

The deploy input should still prefer digests over tags.

## Release Manifest

CI should publish one machine-readable release manifest per release.

Required top-level content:

- `app_version`
- `git_tag`
- `git_sha`
- `bootstrap.postgres_seed_version`
- `bootstrap.image_catalog_run_id`
- `ui_image.digest_ref`
- `backend_image.digest_ref`

The implemented manifest writer lives at
`scripts/deploy/write_release_manifest.py`.
That script is the canonical serializer for the release manifest until a later
deploy tool replaces it.

## Build-Time Versus Runtime Configuration

The build should be as secret-free as possible.

Build-time inputs may include:

- lockfiles and source code
- non-secret build metadata
- public Next.js flags that are intentionally part of the browser bundle

Build-time inputs should not include:

- database credentials
- AWS credentials for runtime service access
- model-provider API keys
- long-lived secrets of any kind

Runtime configuration belongs outside the images.

The explicit deploy contract for that runtime configuration lives in
`docs/deployment_runtime_contract.md`.

## CI Responsibilities

PR CI should continue to focus on:

- lint
- typecheck
- targeted tests
- coverage

Release CI should do the deployment-specific work:

1. resolve the release version
2. build and push both images
3. write the release manifest
4. create the immutable Git tag and GitHub release from the same final
   publication step after the manifest exists
5. describe the current ECS task definitions
6. render new ECS task-definition revisions by replacing:
   - the image digest ref
   - the release-version env value
   - placeholder bootstrap commands with the image-default runtime command
7. run the backend migration task on Fargate
8. run the backend seed-verification task on Fargate
9. update the backend ECS service
10. update the UI ECS service

## Manual Deploy And Rollback

Manual deploys should still exist, but they should use the same ECS path:

- select an immutable Git release tag
- download that tag’s release manifest
- render ECS task-definition revisions from the current baseline
- deploy those revisions to ECS

The manual ref deploy workflow is a separate emergency/operator path. It should
remain digest-driven and may use one unique per-run image tag as a temporary
push handle, but it must not try to publish canonical immutable release tags
such as `vX.Y.Z` or `sha-<commit>`. Those identities belong to the real release
workflow only.

Rollback means redeploying an older immutable release tag. There should not be a
host-local “previous release” mechanism anymore.

## Redundant Old Path

The following old deploy surfaces are intentionally obsolete:

- release-bundle rendering
- SSM command payload rendering
- host-bundle runner scripts
- `docker compose` production deployment
- host-local rollback state

## Verification

Useful verification for this subspec includes:

- local Docker image builds
- manifest writer tests
- ECS task-definition rendering tests
- release-policy validation that `release-please` and manifest helpers agree on
  the plain `vX.Y.Z` tag format
- CI validation that a release can register task-definition revisions and roll
  out services without hand-edited AWS state
