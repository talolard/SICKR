# Release Please And Commit Policy

This subspec defines the near-term release-versioning and commit-style policy
for the deployment project.

Read [00_context.md](./00_context.md) first for the shared deployment context.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) for the
artifact and release-manifest contract this policy feeds.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

Use `release-please` for release preparation, changelog generation, and version
file updates.

Do not treat a merged release PR as a fully published release by itself.

For this repository:

- `main` remains the integration branch
- `release` remains the promotion and publish branch
- conventional-commit intent is enforced at the `main` boundary
- `release-please` maintains the draft release PR on `release`
- the release PR updates `CHANGELOG.md` and `version.txt`
- a separate publish workflow builds and pushes the container images
- the immutable Git tag and GitHub release are created only after both
  containers are built, pushed, version-tagged, and the release manifest exists

This preserves the `main -> release` promotion model while making release
publication depend on real artifacts instead of only on changelog generation.

## Why Release Please Fits Better

`release-please` is a better fit than a fully implicit publish step for this
repo because it separates:

- release preparation
- release review
- release publication

That matters here because the real release artifact is not an npm publish.
The real release artifact is:

- one application version
- one pair of pinned container images
- one release manifest
- one immutable Git tag and GitHub release

We want a release process that is easy for one developer to reason about.
A release PR is easier to inspect and debug than a fully implicit publish step.

## Branch Model

The deployment project currently uses stacked work that descends from
`tal/deployproject`.
That does not replace the application release authority.

The branch roles are:

- stacked deploy work branches -> implementation and review within the
  deployment project
- `main` -> normal integration branch for releasable application history
- `release` -> promotion and publication branch consumed by release tooling

Required branch flow:

1. deployment-project work lands on `tal/deployproject` or a descendant stacked
   branch while the project is in flight
2. releasable changes eventually land in PRs targeting `main`
3. PRs into `main` use conventional-commit-style PR titles
4. PRs into `main` are squash-merged so the resulting commit on `main` carries
   the release intent
5. releasable work is promoted from `main` into `release`
6. promotion from `main` to `release` must preserve the semantic commits that
   `release-please` analyzes
7. do not merge feature branches directly into `release`

Practical promotion rule:

- merge or fast-forward `main` into `release`
- do not squash `main` into `release`
- do not hand-author release commits on `release` except for the
  `release-please` release PR

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
- `build(ci): publish release manifest after image push`
- `feat(api)!: replace thread bootstrap contract`

## Where Enforcement Happens

We do not need to enforce semantic commit messages on every local feature-branch
commit.

The important boundary is the code that lands on `main` and later reaches
`release`.

Required enforcement point:

- PR title enforcement for PRs targeting `main`

Practical rule:

- if a PR targets `main`, its title must be a valid conventional-commit header
- the PR must be squash-merged
- the squash commit message must match the PR title

The concrete enforcement workflow is:

- `.github/workflows/pr-title-main.yml`

## Release PR Behavior

The release-preparation toolchain uses these repo-root files:

- `release-please-config.json`
- `.release-please-manifest.json`
- `CHANGELOG.md`
- `version.txt`

The concrete automation files are:

- `.github/workflows/release-please.yml`
- `.github/workflows/release-publish.yml`

The current helper-config posture is:

- `release-please-config.json` uses the `simple` strategy
- `release-please-config.json` keeps the release PR in draft state by default
- `.release-please-manifest.json` tracks the current published app version

The intended release-PR behavior is:

- `release-please` runs on pushes to `release`
- `release-please` creates or updates one draft release PR on `release`
- the release PR updates `CHANGELOG.md`
- the release PR updates `version.txt`
- Tal can inspect the changelog and version bump before merge
- merging the release PR creates the release commit that publish automation
  treats as the source of truth

The publish workflow currently keys off merged release PRs titled
`chore(release): ...`.
That title shape is therefore part of the release-publication contract and
should stay aligned with the release-please configuration and workflow wiring.

Use the `simple` release strategy unless a stronger repo-specific reason appears
later.
That keeps the release state small and avoids mutating packaging metadata that
is not otherwise part of the deployment contract.

## Changelog And Release Notes

For this repo, changelog generation and final release notes are related but not
the same artifact.

Required behavior:

- `release-please` updates `CHANGELOG.md` on the release PR
- `version.txt` is updated on the same release PR
- the reviewed release PR content is the in-repo source of truth before publish
- the GitHub release is created only after image publication and manifest
  creation succeed
- the GitHub release may generate GitHub-native release notes from the immutable
  tag at final publication time
- the published GitHub release should attach the release manifest so operators
  can retrieve the exact image digests that were released

Operational rule:

- the changelog is the reviewed release-preparation record in Git
- the GitHub release is the external publication record created after artifact
  publication succeeds

## Publication Contract

For this repo, a release is not considered published until all of these are
true:

- the `release-please` release PR has been merged
- both `ui` and `backend` images are built from that merged release commit
- both images are pushed to `ECR`
- both images are tagged with the exact release version
- the release manifest exists and records the exact digests
- the immutable Git tag is created for that same release commit
- the GitHub release is created from that same immutable tag

This is the core invariant:

- changelog preparation alone is not release publication
- artifact publication must succeed before the release becomes official

Recommended publication order:

1. merge the `release-please` release PR on `release`
2. read the app version from the merged release commit
3. build and push both images
4. capture the resulting digests
5. write and publish the release manifest
6. create the immutable Git tag for that same commit
7. create the GitHub release from that immutable tag

## Immutability Rules

Required Git rules:

- release tags use the exact app version, for example `v1.4.2`
- release tags are immutable
- do not create floating Git tags such as `v1`, `v1.4`, `latest`, or `stable`

Required container-tag rules:

- each image gets the exact release version tag, for example `v1.4.2`
- each image also gets an immutable commit-derived tag, for example
  `sha-<commit>`
- do not publish floating container tags such as `latest`, `main`, or
  `release`
- `ECR` tag immutability must prevent overwriting an existing version tag

Operational rule:

- digests remain the source of truth for deployment and rollback
- tags are convenience metadata, not deployment authority

## Authentication And Human Gates

The default GitHub token may be enough for `release-please`, but we should not
assume that.

If `release-please` needs a Tal-provided GitHub token or app credential, treat
that as an explicit Tal-owned gate in the deployment project.

The implemented workflow therefore uses this auth posture:

- default to `github.token`
- allow an override via repository secret `RELEASE_PLEASE_TOKEN`
- if Tal wants release-please-created PRs to trigger additional checks or needs
  stronger branch-protection compatibility, populate `RELEASE_PLEASE_TOKEN` as
  the explicit Tal-owned gate

For artifact publication, the publish workflow also requires the repository
variable `AWS_RELEASE_ROLE_ARN` so GitHub Actions can assume the AWS publish
role by OIDC instead of baking static AWS credentials into CI.

Do not silently widen bot permissions.

## Validation

Useful validation for this subspec means:

- confirm the chosen release model matches the project decisions in
  [multi_agent_review.md](../multi_agent_review.md)
- confirm the Docker/CI contract in
  [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) uses the same
  definition of a published release
- confirm the branch rules do not contradict the stacked-branch rule from
  [guiding_principles.md](../guiding_principles.md)
- confirm the helper config and workflow names referenced here match the
  repository files that currently implement the release-policy surface

## Summary

The near-term release policy should be:

- conventional commits on `main`
- promotion from `main` to `release` without squashing away releasable history
- `release-please` prepares the draft release PR on `release`
- merging that PR updates the changelog and version file
- separate automation builds and publishes images plus the release manifest
- only then do we create the immutable tag and GitHub release
