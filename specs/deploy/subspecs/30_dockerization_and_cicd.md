# Dockerization And CI/CD

This subspec covers the deploy-facing container and CI/CD contract for the
near-term deployment.

Read [00_context.md](./00_context.md) first for the shared goals and high-level
deployment decisions.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

For this deployment phase, we should build and release exactly two application
images:

- one `ui` image for the Next.js app
- one `backend` image for the FastAPI + AG-UI runtime

Those images should be built in CI, pushed to `ECR`, and deployed by exact
immutable references.

The deploy contract between CI and infra should be a small release manifest that
names:

- the application release version
- the released Git commit
- the exact `ui` image reference and digest
- the exact `backend` image reference and digest

Infra should consume that manifest or the equivalent explicit image references.
Deploy should not rebuild images on the host.

## Why This Is Separate

This is a separate decision from Terraform and AWS topology.

The CI/CD system needs a stable artifact contract even if we later change:

- the Terraform module layout
- the exact host bootstrap details
- the deploy trigger mechanism
- how many AWS resources are managed up front

The key point is that downstream infra consumes pinned application artifacts,
not source code and not ad hoc host-local builds.

## Image Set

Only two deployable application images are in scope now:

- `ui`
- `backend`

Do not introduce extra deployable images yet for:

- `nginx` or `Caddy` customization
- migration runners
- data-seed jobs
- local developer dependencies

If later infra needs a reverse-proxy image or one-off job image, that can be
specified separately. The near-term app release unit is still just `ui` plus
`backend`.

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
- `docker/env/host.env.example`
- `scripts/deploy/read_release_version.py`
- `scripts/deploy/write_release_manifest.py`
- `docs/deployment_runtime_contract.md`

The current build posture intentionally targets `linux/amd64` for release
publication.
That is a dependency-compatibility decision, not a scale decision.
It exists because the current Python runtime dependency set includes packages
such as `usd-core` that do not publish the needed wheels for `linux/arm64`.

## Registry Contract

`ECR` is the target registry for both images.

Recommended repo shape:

- one ECR repo for `ui`, named `ikea-agent/ui`
- one ECR repo for `backend`, named `ikea-agent/backend`

Tagging posture:

- every release gets one app-level `release-please` version
- both images are published under that exact immutable release version tag
- both images should also carry the exact released commit SHA as a secondary
  immutable tag
- no floating tags such as `latest`, `main`, or `release` should be published

The deploy input should still prefer digests over tags.

Operational rule:

- tags are for discovery and operator convenience
- digests are the source of truth for deployment and rollback

## Release Manifest

CI should publish one machine-readable release manifest per release.

Suggested shape:

```json
{
  "app_version": "1.4.2",
  "git_tag": "v1.4.2",
  "git_sha": "abc1234def5678",
  "ui_image": {
    "repository": "…/ui",
    "version_tag": "v1.4.2",
    "commit_tag": "sha-abc1234def5678",
    "digest": "sha256:…"
  },
  "backend_image": {
    "repository": "…/backend",
    "version_tag": "v1.4.2",
    "commit_tag": "sha-abc1234def5678",
    "digest": "sha256:…"
  }
}
```

The exact serialization format can be JSON or another simple machine-readable
format. The important part is that downstream deploy tooling receives one
coherent release record for both services.

The implemented manifest writer lives at
`scripts/deploy/write_release_manifest.py`.
That script is the canonical serializer for the release manifest until a later
deploy tool replaces it.

`git_sha` must be the exact commit targeted by the immutable release tag.
For this repo, that means the merged `release-please` release-PR commit that is
used to build and publish the release artifacts.

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

The explicit deploy contract for that runtime configuration now lives in
`docs/deployment_runtime_contract.md`.

Expected runtime-only values include:

- `DATABASE_URL`
- model-provider credentials such as `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `FAL_KEY` or `FAI_AI_API_KEY`
- `PY_AG_UI_URL` for the `ui` container's server-side calls to the backend
- `IMAGE_SERVING_STRATEGY=direct_public_url`
- private artifact-storage configuration
- observability credentials and environment metadata

Near-term rule:

- the `ui` image should be reusable across environments as much as possible
- if a value must be visible in browser code, treat it as a deliberate public
  build-time input
- otherwise prefer server-side runtime configuration

For this deployment phase, the default production posture should be:

- `NEXT_PUBLIC_USE_MOCK_AGENT=0`
- `NEXT_PUBLIC_TRACE_CAPTURE_ENABLED=0`

## CI Responsibilities

The current repo already has strong PR CI for lint, typecheck, unit tests,
coverage, and deferred real-backend smoke.

For this deployment phase, CI responsibilities should be split into two layers.

### PR CI

PR CI should continue to do verification only.

It should:

- run the existing backend and frontend quality gates
- run the deferred real-backend smoke path
- confirm the code is releasable

It should not:

- push release images
- mutate deployed infrastructure
- run production migrations
- seed production data
- require production secrets

### Release CI/CD

Release automation should start only after code has already passed normal CI.
For this phase, it should run from the release branch or an equivalent tagged
release ref, not from every successful `main` push.

Release automation should:

- resolve the release version from the merged `release-please` release-PR
  commit, as defined in
  [40_semantic_release_and_commit_policy.md](./40_semantic_release_and_commit_policy.md)
- build `ui` and `backend` images once
- push both images to `ECR`
- tag both images with the release version and the exact released
  commit SHA
- capture the resulting digests
- publish the release manifest
- create the immutable Git tag and GitHub release only after artifact
  publication succeeds
- trigger deployment using those exact immutable references

The concrete workflow split is:

- `.github/workflows/release-please.yml` prepares and updates release PRs on
  `release`
- `.github/workflows/release-publish.yml` runs only after a merged
  `chore(release): ...` PR on `release`, then builds images, pushes them,
  writes the manifest, and only then creates the immutable tag and GitHub
  release

For release publication, the current workflow expects the repository variable
`AWS_RELEASE_ROLE_ARN` so GitHub Actions can assume the publish role via OIDC
before pushing to ECR.

The deploy step should be separate from image build, even if both happen in the
same workflow file.

## Deployment Interface To Infra

This subspec intentionally does not choose the exact Terraform module layout or
host bootstrap script.

It does define the interface that infra should expect:

- infra provides an environment that can pull the `ui` and `backend` images from
  `ECR`
- infra injects runtime configuration and secrets at container start
- infra runs schema migration and any required bootstrap step before normal app
  traffic is considered healthy
- infra deploys by pinned image digests, not by floating tags

If the deploy mechanism is `SSM + docker compose`, it should consume the release
manifest or equivalent explicit digest inputs.

If that mechanism later changes, the artifact contract should stay the same.

## Health And Deployment Gates

Before a new release is considered live, deploy automation should verify at
least:

- `ui` starts and serves normal app pages
- `backend` starts and serves its health or metadata endpoints
- the `ui` can reach the backend over the configured internal `PY_AG_UI_URL`
- required migrations have completed
- required seed/bootstrap state exists for the deployed app mode

This spec does not require a full synthetic test suite in deploy.
It does require a minimal post-deploy health gate before the release is treated
as successful.

## Rollback Posture

Rollback should be simple:

- redeploy the previous known-good release manifest
- repin both services to the earlier image digests

That means:

- deployment history must preserve prior release manifests
- the host should not depend on mutable `latest` tags
- image retention in `ECR` must be compatible with keeping recent rollback
  candidates

Database migrations are the main rollback risk.

Near-term operational rule:

- destructive or hard-to-reverse schema changes should not be assumed safe for
  instant rollback
- rollout sequencing for those migrations may require a separate manual step or
  later spec

## What CI/CD Should Not Do Yet

For this phase, do not add:

- Kubernetes or GitOps platform machinery
- multiple environment promotion layers beyond the existing release posture
- blue/green or canary rollout systems
- host-local image builds during deploy
- CloudFront invalidation as a normal part of app deploy

Product images are already expected to use immutable object keys, so normal app
deploys should not depend on CDN invalidation.

## Explicit Deferrals

This subspec intentionally defers:

- the exact Dockerfile contents
- the exact GitHub Actions workflow names and triggers for release
- the exact deploy runner implementation on the host
- the exact migration and bootstrap commands
- vulnerability-scanning policy beyond basic registry support
- semver automation details
- exact secret-store wiring and rotation policy

## Summary

The near-term Dockerization and CI/CD shape is:

- two deployable images: `ui` and `backend`
- CI builds them once per release and pushes them to `ECR`
- CI emits one release manifest containing both pinned image digests
- infra deploys those exact artifacts and injects runtime config externally
- PR CI stays verification-only
- rollback is redeploying the previous pinned release
