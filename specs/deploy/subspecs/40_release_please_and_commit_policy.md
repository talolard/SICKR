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

Chosen target model for this repository:

- `main` remains the integration branch
- `release` remains the promotion and publish branch
- conventional-commit intent is enforced at the `main` boundary
- `release-please` maintains the draft release PR on `release`
- the release PR updates `CHANGELOG.md` and `version.txt`
- the publish flow uses the release version prepared on `release` to build and
  push the container images
- the immutable Git tag and GitHub release are created only after both
  containers are built, pushed, version-tagged, and the release manifest exists
- deploy runs automatically from the successful canonical release flow
- the manual source-ref deploy path is removed rather than preserved as a
  second steady-state release lane

This preserves the `main -> release` promotion model while making release
publication depend on real artifacts instead of only on changelog generation.

Current implementation honesty note:

- the repo has the release-preparation and release-publication workflows
- the repo does not yet prove the full target contract end to end
- `origin/release` already carries release-preparation state through `0.4.0`,
  but the repo still has no published Git tags or GitHub releases
- the current publication handoff still accepts only a merged PR into `release`
  whose title starts with `chore(release):`, which is weaker than a
  Release-Please-owned handoff
- the current `main` copy of `.github/workflows/release-publish.yml` is not a
  trustworthy executable contract because it contains a YAML parsing regression
- the current tag identity is plain `vX.Y.Z`; the older `designagent-vX.Y.Z`
  component-prefixed form is obsolete and should not reappear
- stronger provenance and promotion-boundary enforcement are still unresolved

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

Current repository-state note:

- `origin/release` now exists and is actively used by `release-please`
- release-preparation PRs through `0.4.0` have already been merged there
- the repo still does not have the matching immutable publication record of Git
  tags and GitHub releases

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

Current enforcement note:

- the repo currently enforces PR-title shape on PRs targeting `main`
- the repo does not yet enforce history-preserving promotion from `main` to
  `release`
- that promotion rule is still policy, not a mechanically enforced boundary

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
- `release-please-config.json` uses plain `vX.Y.Z` tags without a component
  prefix
- `.release-please-manifest.json` tracks the current release-preparation version
  on `release`; by itself it is not proof of a published immutable release

Intended release-PR behavior:

- `release-please` runs on pushes to `release`
- `release-please` creates or updates one draft release PR on `release`
- the release PR updates `CHANGELOG.md`
- the release PR updates `version.txt`
- Tal can inspect the changelog and version bump before merge
- merging the release PR creates the release commit that publish automation
  treats as the source of truth

Repository gate:

- if the default `GITHUB_TOKEN` cannot create or update release PRs in this
  repository, configure `RELEASE_PLEASE_TOKEN` with the minimum scope needed to
  manage release PRs

The current publish workflow still keys off merged release PRs titled
`chore(release): ...`.
That title coupling is transitional debt, not the desired long-term
release-publication contract.

Current provenance note:

- the title-prefix check is weaker than verifying that the merged PR was
  actually produced by `release-please`
- the current docs must not describe that as stronger provenance than it is

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
- the GitHub release creation step is also the immutable tag creation step, so
  the release record and tag are created from the same action against the same
  commit
- the GitHub release may generate GitHub-native release notes from the immutable
  tag at final publication time
- the published GitHub release should attach the release manifest so operators
  can retrieve the exact image digests that were released

Operational rule:

- the changelog is the reviewed release-preparation record in Git
- the GitHub release is the external publication record created after artifact
  publication succeeds

## Publication Contract

Target publication invariant for this repo:

- a release should not be considered published until all of these are true:
  - the `release-please` release PR has been merged
  - both `ui` and `backend` images are built from that merged release commit
  - both images are pushed to `ECR`
  - both images are tagged with the exact release version
  - the release manifest exists and records the exact digests
  - the ECS deploy workflow can consume that manifest without rebuilding or
    retagging images
  - the immutable Git tag is created for that same release commit
  - the GitHub release is created from that same immutable tag

That is the intended invariant. It is not yet fully guaranteed by the current
workflow implementation.

Current repo reality:

- a merged PR into `release` with a `chore(release): ...` title can trigger the
  publish workflow
- the workflow resolves the release version from the checked-out release ref
- the workflow builds and pushes both images before writing the release manifest
- the workflow attempts to create the GitHub release from the exact release
  commit only after image publication and manifest creation
- the automatic ECS deploy work happens after publication inside the canonical
  release flow
- the repo also still contains `manual-ref-deploy.yml`, but that is not part of
  the intended long-term publication contract

Current unresolved gap:

- changelog preparation alone is not release publication
- the publish handoff is still title-based instead of being owned directly by
  Release Please outputs
- prepared release state on `release` has already advanced beyond published
  immutable release state
- the current `main` publish workflow is broken, so the canonical path is not
  yet trustworthy enough to replace recovery tooling
- the `main -> release` promotion boundary is still policy, not mechanism

Desired hardening still outstanding:

1. prove or enforce that the publish path comes only from the real
   `release-please` release PR
2. make the final publication step failure-safe and trustworthy
3. remove the manual source-ref deploy lane instead of preserving it as a
   parallel path
4. enforce the `main -> release` promotion rule rather than leaving it as prose

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
role by OIDC instead of baking static AWS credentials into CI. That role trust
currently allows both the `release` branch and `main` because the repo still
contains the transitional `manual-ref-deploy` workflow.

Target posture:

- the normal publish path runs from `release`
- the extra `main` trust should be removed with the manual source-ref deploy
  lane

Do not silently widen bot permissions.

## Validation

Useful validation for this subspec means:

- confirm the chosen release model matches the current top-level deploy spec in
  [final_deployment_recommendation_2026-03-24_synthesized.md](../final_deployment_recommendation_2026-03-24_synthesized.md)
- confirm the Docker/CI contract in
  [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) uses the same
  definition of a published release
- confirm the branch rules do not contradict the stacked-branch rule from
  [guiding_principles.md](../guiding_principles.md)
- confirm the helper config and workflow names referenced here match the
  repository files that currently implement the release-policy surface
- check the workflow trigger conditions and publication ordering before claiming
  any release-safety guarantee
- check whether the documented current-state notes still match the real
  `release` branch, current workflows, and current GitHub release state

## Summary

The near-term release policy target is:

- conventional commits on `main`
- promotion from `main` to `release` without squashing away releasable history
- `release-please` prepares the draft release PR on `release`
- merging that PR updates the changelog and version file
- separate automation builds and publishes images plus the release manifest
- only then do we create the immutable tag and GitHub release

What is true today:

- `release-please` is the chosen preparation tool and the repo contains the
  supporting config and workflows
- `origin/release` exists and carries release-preparation history
- PR-title enforcement exists for PRs targeting `main`
- publication is currently keyed off a merged `chore(release): ...` PR, not
  stronger `release-please` provenance
- prepared release state has advanced further than published immutable release
  state
- the `manual-ref-deploy` workflow still exists, but it is recovery debt rather
  than intended steady-state release machinery
- the `main -> release` promotion rule is still documented policy rather than
  enforced repository behavior
