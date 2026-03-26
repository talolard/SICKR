# Release Please And Commit Policy

This subspec defines the near-term release-versioning and commit-style policy
for the deployment project.

Read [00_context.md](./00_context.md) first for the shared deployment context.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) for the
artifact and release-manifest contract this policy feeds.
Read [docs/release_automation.md](../../docs/release_automation.md) for the
operator-facing workflow summary.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

Use `release-please` for release preparation, changelog generation, version
file updates, Git tag creation, and GitHub release creation.

Do not use a long-lived `release` branch.

Chosen target model for this repository:

- `main` remains the integration branch and the release authority
- conventional-commit intent is enforced at the `main` boundary
- `release-please` maintains one draft release PR against `main`
- the release PR updates `CHANGELOG.md` and `version.txt`
- merging that release PR creates the immutable Git tag and GitHub release
- the published GitHub release triggers image publication and manifest upload
- the published release manifest is the deploy handoff into ECS
- automatic deploy runs from the published release artifact set
- manual redeploy stays on immutable published release tags

## Why This Fits Better

`release-please` is a better fit than a home-grown versioning path because it
separates:

- release preparation
- release review
- release publication

That separation still matters here, but the target branch should be `main`
rather than a second long-lived branch. Using `release` for release-preparation
commits caused branch drift by design and made the promotion boundary more
complicated than the actual deployment contract required.

The real published release artifact is:

- one application version
- one immutable Git tag and GitHub release
- one pair of pinned container images
- one release manifest that records the exact digests and bootstrap inputs

## Branch And Trigger Model

The deployment project may still use stacked implementation branches below
`tal/deployproject`, but that does not change release authority.

Current branch roles:

- stacked deploy work branches -> implementation and review within the
  deployment project
- `main` -> normal integration branch and release-preparation branch
- immutable Git tags `vX.Y.Z` -> publication and redeploy authority

Required flow:

1. releasable work lands in PRs targeting `main`
2. PRs into `main` use conventional-commit-style PR titles
3. PRs into `main` are squash-merged so the resulting commit on `main` carries
   the release intent
4. `release-please` runs on pushes to `main`
5. `release-please` creates or updates one draft release PR against `main`
6. merging that release PR creates the immutable Git tag and GitHub release
7. `Release Publish` runs from the published release event, builds images,
   writes `release-manifest.json`, and uploads the manifest to the GitHub
   release
8. `Release Deploy` deploys by immutable tag and manifest, either from the
   automatic path or manual redeploy dispatch

There is no longer a supported `main -> release` promotion lane.

## Commit Policy

Use conventional-commit-style release intent.

Required releasable commit types:

- `feat:` -> minor release
- `fix:` -> patch release
- `perf:` -> patch release
- `revert:` -> patch release
- `deps:` -> patch release
- `type(scope)!:` or a `BREAKING CHANGE:` footer -> major release

Allowed non-releasable commit types:

- `docs:`
- `test:`
- `refactor:`
- `build:`
- `ci:`
- `chore:`
- `style:`

Required message shape:

```text
type(scope): short summary
```

Examples:

- `feat(search): add retailer fallback for missing dimensions`
- `fix(ui): preserve trace state on refresh`
- `build(ci): upload release manifest to GitHub release`
- `feat(api)!: replace thread bootstrap contract`

## Where Enforcement Happens

We do not need to enforce semantic commit messages on every local feature-branch
commit.

The important boundary is the code that lands on `main`.

Required enforcement point:

- PR title enforcement for PRs targeting `main`

The concrete enforcement workflow is:

- `.github/workflows/pr-title-main.yml`

The deleted `release`-branch governance workflows were transitional debt from
the old promotion model and are no longer part of the intended path.

## Release PR Behavior

The release-preparation toolchain uses these repo-root files:

- `release-please-config.json`
- `.release-please-manifest.json`
- `CHANGELOG.md`
- `version.txt`

The concrete automation files are:

- `.github/workflows/release-please.yml`
- `.github/workflows/release-publish.yml`
- `.github/workflows/release-deploy.yml`

The current helper-config posture is:

- `release-please-config.json` uses the `simple` strategy
- `release-please-config.json` keeps the release PR in draft state by default
- `release-please-config.json` uses plain `vX.Y.Z` tags without a component
  prefix
- `release-please-config.json` uses `bootstrap-sha` to ignore the repo's older
  non-conventional history and start the main-based release model from the
  migration baseline
- `.release-please-manifest.json` records the current release baseline version

Intended release-PR behavior:

- `release-please` runs on pushes to `main`
- `release-please` creates or updates one draft release PR on `main`
- the release PR updates `CHANGELOG.md`
- the release PR updates `version.txt`
- Tal can inspect the changelog and version bump before merge
- merging the release PR creates the immutable Git tag and GitHub release

## Authentication And Workflow Chaining

`RELEASE_PLEASE_TOKEN` is required for this repo's release automation.

Why:

- `release-please` must create PRs, tags, and GitHub releases
- the downstream publish workflow is triggered by the GitHub release event
- resources created with the built-in `GITHUB_TOKEN` do not trigger later
  workflows, except for `workflow_dispatch` and `repository_dispatch`

Therefore:

- do not fall back to `github.token` for `release-please`
- treat `RELEASE_PLEASE_TOKEN` as an explicit Tal-owned release gate
- keep the token scope minimal while still allowing release PR and release
  creation

For AWS artifact publication and deploy:

- the publish workflow requires `AWS_RELEASE_ROLE_ARN`
- the deploy workflow requires `AWS_DEPLOY_ROLE_ARN`
- Terraform should allow GitHub OIDC subjects from `refs/heads/main` and
  `refs/tags/v*`

## Publication Contract

Target publication invariant for this repo:

- a release is not considered published until all of these are true:
  - the Release Please PR on `main` has merged
  - the immutable Git tag and GitHub release exist
  - both `ui` and `backend` images are built and pushed for that tag
  - the release manifest exists and records the exact digests
  - the GitHub release carries the release manifest as an asset
  - ECS deploy automation can consume that manifest without rebuilding or
    retagging images

That means changelog preparation alone is not publication, and GitHub release
creation alone is not enough either.

## Redeploy And Rollback

Rollback and redeploy should both use immutable published tags.

Required behavior:

- `Release Deploy` accepts a release tag by `workflow_dispatch`
- it downloads that tag's `release-manifest.json`
- it renders task-definition revisions from the Terraform-owned baseline
- it redeploys those exact image digests to ECS

There should not be a source-ref rebuild workflow in the steady-state path.

## Validation

Useful validation for this subspec means:

- confirm the chosen release model matches the top-level deploy spec and the
  runtime contract
- confirm the workflow trigger ordering still matches the intended invariant:
  `main` release PR -> GitHub release -> publish -> deploy
- confirm the helper config and workflow names referenced here match the
  repository files that currently implement the release-policy surface
- confirm old `autorelease:*` labels from the retired `release` branch path do
  not remain on merged PRs in a way that would block the new model
- check that manual redeploy still works by immutable tag after publish changes

## Summary

The near-term release policy target is:

- conventional commits on `main`
- one draft Release Please PR on `main`
- merge that PR to create the immutable tag and GitHub release
- publish images and release manifest from the published release event
- deploy and redeploy only from immutable published release tags
