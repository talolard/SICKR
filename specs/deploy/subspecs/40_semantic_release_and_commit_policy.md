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
- `release` remains the publishing branch
- conventional-commit intent is enforced at the `main` boundary
- `release-please` maintains the release PR on `release`
- the release PR updates `CHANGELOG.md` and `version.txt`
- a separate publish workflow builds and pushes the container images
- the immutable Git tag and GitHub release are created only after both
  containers are built, pushed, version-tagged, and the release manifest exists

This preserves the `main -> release` promotion model while making release
publication depend on real artifacts instead of only on changelog generation.

## Why Release Please Fits Better

`release-please` is a better fit than `semantic-release` for this repo because
it separates:

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

## Branch Workflow

Required branch flow:

1. feature work lands in PRs targeting `main`
2. PRs into `main` use conventional-commit-style PR titles
3. PRs into `main` are squash-merged so the resulting commit on `main` carries
   the release intent
4. releasable work is promoted from `main` into `release`
5. `release-please` runs on `release` and creates or updates a release PR
6. merging that release PR updates `CHANGELOG.md` and `version.txt` on `release`
7. publish automation runs from that merged release commit
8. only after artifact publication succeeds do we create:
   - the immutable `vX.Y.Z` Git tag
   - the GitHub release

Do not squash `main` into `release`.
Promotion from `main` to `release` should preserve the semantic commits that
`release-please` must analyze.

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

We do not need to enforce semantic commit messages on every local feature branch
commit.

The important boundary is the code that lands on `main` and later reaches
`release`.

Required enforcement point:

- PR title enforcement for PRs targeting `main`

Practical rule:

- if a PR targets `main`, its title must be a valid conventional-commit header
- the PR must be squash-merged
- the squash commit message must match the PR title

## Release Please Files

The release-preparation toolchain should use repo-root files:

- `release-please-config.json`
- `.release-please-manifest.json`
- `CHANGELOG.md`
- `version.txt`

The intended posture is:

- `release-please` updates `CHANGELOG.md`
- `release-please` updates `version.txt`
- application release automation reads the version from the merged release
  commit, not from an inferred Git tag that does not exist yet

Use the `simple` release strategy unless a stronger repo-specific reason appears
later.
That keeps the release state small and avoids mutating packaging metadata that
is not otherwise part of the deployment contract.

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

## Summary

The near-term release policy should be:

- conventional commits on `main`
- promotion from `main` to `release`
- `release-please` prepares the release PR on `release`
- merging that PR updates the changelog and version file
- separate automation builds and publishes images
- only then do we create the immutable tag and GitHub release
