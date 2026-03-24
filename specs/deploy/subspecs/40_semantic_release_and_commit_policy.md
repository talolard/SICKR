# Semantic Release And Commit Policy

This subspec defines the release-versioning and commit-style policy for the
near-term deployment.

Read [00_context.md](./00_context.md) first for the shared deployment context.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) for the
artifact and release-manifest contract this policy feeds.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

Use `semantic-release` as the only authority for application version numbers,
Git tags, and GitHub release notes.

For this repository:

- `main` is the integration branch
- `release` is the only publishing branch
- semantic-release runs only on `release`
- conventional commit intent is enforced at the `main` boundary
- machine-generated release notes are published to GitHub Releases
- a machine-generated `CHANGELOG.md` is auto-updated on `release`
- we do not commit version bumps back into the repository

This keeps the `main -> release` promotion model while still letting
semantic-release determine the version automatically from commit history.

## Why This Fits The Branch Model

semantic-release can be configured with custom release branches, and it expects
all releases to happen only from the configured release branches.

For this repo, the clean rule is:

- `main` collects validated work
- promotion from `main` to `release` decides what is releasable
- semantic-release runs on `release` and creates the tag for what was promoted

Do not configure both `main` and `release` as semantic-release publishing
branches.
That adds unnecessary version-order constraints and can trigger
`EINVALIDNEXTVERSION` conflicts if both branches attempt to publish overlapping
version lines.

## Required Branch Workflow

The required branch workflow is:

1. Feature work lands in PRs targeting `main`.
2. PRs into `main` must use a conventional-commit-style PR title.
3. PRs into `main` must be squash-merged so the resulting commit on `main`
   matches the semantic PR title.
4. A release is created by promoting `main` into `release`.
5. A push to `release` runs semantic-release.
6. semantic-release computes the next version, creates the immutable Git tag,
   updates `CHANGELOG.md`, creates the GitHub release, and hands that version
   to the release workflow.

Promotion from `main` to `release` must preserve the semantic commits already on
`main`.
A fast-forward or normal merge is acceptable.
Do not squash `main` into `release`, because that would collapse many release
signals into one artificial promotion commit.

## Commit Policy

The repository should use conventional-commit-style release intent.

Required commit types and their release meaning:

- `feat:` -> minor release
- `fix:` -> patch release
- `perf:` -> patch release
- `revert:` -> patch release
- `type(scope)!:` or a `BREAKING CHANGE:` footer -> major release

Allowed non-release types:

- `docs:`
- `test:`
- `refactor:`
- `build:`
- `ci:`
- `chore:`
- `style:`

Those non-release types are allowed in history, but by default they should not
trigger a release.

Required message shape:

```text
type(scope): short summary
```

Examples:

- `feat(search): add retailer fallback for missing dimensions`
- `fix(ui): preserve trace state on refresh`
- `refactor(agent): simplify room extraction pipeline`
- `feat(api)!: replace thread bootstrap contract`

For breaking changes, either of these is acceptable:

- `feat(api)!: replace thread bootstrap contract`
- a normal header plus a `BREAKING CHANGE:` footer in the body

## Where Enforcement Happens

We do not need to force every local feature-branch commit to be semantic.
The important thing is that the commits that actually land on `main` and later
reach `release` carry valid release intent.

Therefore the required enforcement point is:

- PR title enforcement for PRs targeting `main`

The practical rule is:

- if a PR targets `main`, its title must be a valid conventional commit header
- the PR must be squash-merged
- the squash commit message must be the PR title

This achieves the user goal of enforcing semantic commits on `main` without
making every work-in-progress branch painful.

## Merge Policy

Required merge policy:

- squash merge for PRs into `main`
- no direct commits to `main`
- no direct commits to `release` except controlled promotion or emergency revert
- promotion from `main` to `release` via merge or fast-forward, not squash

Why this policy:

- squash merge gives one clean semantic commit per PR on `main`
- release analysis becomes predictable
- promotion to `release` preserves the semantic commits semantic-release must
  analyze

If an urgent bad release must be fixed:

- revert or fix it on `release`
- let semantic-release produce the next corrective release

Do not delete published release tags.

## semantic-release Configuration

Use a root-level `release.config.cjs`.

Required configuration posture:

- `branches: ["release"]`
- keep `tagFormat: "v${version}"`
- disable the default npm publishing assumptions
- publish GitHub Releases as the canonical machine-generated release notes
- update a root `CHANGELOG.md` file on each release
- use GitHub releases and repo-local scripts instead of package-registry
  publishing

Recommended plugin set:

- `@semantic-release/commit-analyzer`
- `@semantic-release/release-notes-generator`
- `@semantic-release/changelog`
- `@semantic-release/git`
- `@semantic-release/github`
- `@semantic-release/exec`

Use `@semantic-release/git` only to commit the generated changelog.
Do not use it to commit version bumps, lockfile churn, or generated build
artifacts.

Do not use `@semantic-release/npm` in v1 unless the repo later becomes an npm
package publisher.

Recommended `release.config.cjs` shape:

```js
/**
 * @type {import('semantic-release').GlobalConfig}
 */
module.exports = {
  branches: ["release"],
  tagFormat: "v${version}",
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    [
      "@semantic-release/changelog",
      {
        changelogFile: "CHANGELOG.md",
        changelogTitle: "# Changelog",
      },
    ],
    [
      "@semantic-release/git",
      {
        assets: ["CHANGELOG.md"],
        message:
          "chore(release): ${nextRelease.version} [skip ci]\\n\\n${nextRelease.notes}",
      },
    ],
    [
      "@semantic-release/exec",
      {
        verifyReleaseCmd:
          "./scripts/release/verify-release.sh ${nextRelease.version}",
        publishCmd:
          "./scripts/release/publish-release.sh ${nextRelease.version}",
      },
    ],
    "@semantic-release/github",
  ],
};
```

The exact script names can differ.
The important contract is:

- semantic-release computes the version
- semantic-release writes the GitHub release notes and updates `CHANGELOG.md`
- repo-local scripts build and publish artifacts using that version
- GitHub release metadata is published from the same run

Plugin ordering matters:

- `@semantic-release/changelog` must run before `@semantic-release/git`
- `@semantic-release/git` should commit only `CHANGELOG.md`

## Release Records And Immutability

Each release must produce three immutable identifiers:

- one Git tag: `vX.Y.Z`
- one GitHub release for `vX.Y.Z`
- one pair of container images tagged from the semantic-release output

Required Git rules:

- release tags must use the exact semantic-release output, for example `v1.4.2`
- release tags must never be moved or deleted
- do not create floating Git tags such as `v1`, `v1.4`, `latest`, or `stable`

Required container-tag rules:

- tag each image with the exact release version, for example `v1.4.2`
- tag each image with the exact released commit SHA, for example
  `git-<full-sha>` or `sha-<full-sha>`
- do not push floating container tags such as `latest`, `main`, `release`, or
  mutable major/minor aliases
- ECR repository immutability must prevent reusing an existing tag name for a
  different image

Required deployment rule:

- deployments use image digests from the release manifest as the source of truth
- semantic version tags and commit-SHA tags exist for operator visibility and
  traceability, not as mutable deployment pointers

Canonical release identity:

- the immutable Git tag and GitHub release identify the released code revision
- the release manifest identifies the exact immutable image digests built from
  that release
- the committed `CHANGELOG.md` is convenience documentation and should match the
  GitHub release notes, but the tag and manifest remain the canonical release
  records

## Changelog Policy

We accept the extra complexity of a committed changelog because the user wants a
file-based release history in the repository, not only GitHub Releases.

Required changelog rules:

- `CHANGELOG.md` lives at repo root
- it is updated only by semantic-release on `release`
- human edits to release sections are not the source of truth
- manual edits are allowed only for top-level explanatory text outside generated
  release entries

Operational note:

- the latest auto-updated `CHANGELOG.md` is guaranteed on `release`
- `main` does not need to carry the latest changelog commit
- GitHub Releases remain the canonical public release-notes surface

## Bot Credentials And Branch Protection

Because `@semantic-release/git` pushes a changelog commit back to the release
branch, the release bot needs push permission to `release`.

Required policy:

- the default `GITHUB_TOKEN` is acceptable only if it can both create releases
  and push the changelog commit to `release`
- if branch protection blocks that, use a dedicated bot credential with the
  minimum rights needed to push the changelog commit and create releases
- prefer a narrowly scoped bot identity over a broad personal token

The release commit message must include `[skip ci]` to avoid unnecessary
follow-on builds from the changelog commit.

## Low-Complexity Goodies

These are worth enabling because they add useful automation without changing the
branch model:

- keep `@semantic-release/github` enabled so GitHub Releases are published
  automatically
- allow the GitHub plugin to annotate released PRs and issues
- keep Git tags in the default `v${version}` format for predictable tooling
- run the release job on the latest available Node LTS that satisfies
  semantic-release requirements

## CI Layout

Required CI split:

### PR Validation

For PRs targeting `main`, CI should:

- run normal `pr-ci`
- run a semantic PR-title check

This job should fail if the PR title is not a valid conventional commit header.

### Release Workflow

The release workflow should trigger on:

- pushes to `release`
- optional manual `workflow_dispatch`

The release job must run only after the normal validation checks are green.

The release job should:

1. check out the repository with full history and tags
2. install Node and the semantic-release toolchain
3. run semantic-release
4. let semantic-release determine `nextRelease.version`
5. build and push the `ui` and `backend` images tagged with both:
   - `v${nextRelease.version}`
   - `sha-<released-commit-sha>`
6. publish the release manifest described in
   [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md)
7. create the Git tag and GitHub release

The release job must have permission to create tags and GitHub releases.
It must not run before test jobs succeed.

Release-identity rule:

- the version tag, GitHub release, committed `CHANGELOG.md`, release manifest,
  and container `sha-*` tags must all refer to the same released commit
- do not assume the workflow's initial `GITHUB_SHA` is that released commit if
  semantic-release creates a changelog commit during the run
- the release scripts must resolve the effective released commit SHA from the
  release workspace and use that value for image SHA tags and the manifest

## Local Developer Experience

Local hooks should help, not block the repo unnecessarily.

Required local-policy posture:

- CI enforcement is mandatory
- local commit-style hooks are optional but recommended

Use a `commit-msg` hook rather than a `pre-commit` hook for semantic-commit
validation.
Commit style is a property of the commit message, so `pre-commit` is the wrong
hook for strict enforcement.

Recommended local tooling:

- `commitlint.config.cjs` at repo root
- either `husky` or `lefthook` for a `commit-msg` hook

Recommended local rule:

- developers may use the `commit-msg` hook locally if they want immediate
  feedback
- CI remains the source of truth

## Files That Should Exist

The repo should eventually contain:

- `release.config.cjs`
- `commitlint.config.cjs`
- `CHANGELOG.md`
- `.github/workflows/release.yml`
- `.github/workflows/semantic-pr-title.yml`
- `scripts/release/verify-release.sh`
- `scripts/release/publish-release.sh`

Recommended additional tooling file:

- a small root `package.json` dedicated to release-tooling dependencies

That root `package.json` should hold:

- `semantic-release`
- `@semantic-release/commit-analyzer`
- `@semantic-release/release-notes-generator`
- `@semantic-release/changelog`
- `@semantic-release/git`
- `@semantic-release/github`
- `@semantic-release/exec`
- `@commitlint/cli`
- `@commitlint/config-conventional`
- optional hook tooling such as `husky` or `lefthook`

The repo already has `ui/package.json`, but release tooling is repository-wide,
not UI-specific, so it should not be hidden inside the `ui` workspace.

## What We Do Not Do

For this phase, do not do the following:

- do not run semantic-release on `main`
- do not run semantic-release on feature branches
- do not require every local branch commit to be semantic
- do not commit version bumps back into the repo
- do not maintain a hand-edited changelog as the release source of truth
- do not let image-build scripts invent their own version independently of
  semantic-release
- do not publish mutable Git tags or mutable container tags

## Verification

When implemented, verify the policy with these checks:

### Branch And Config Checks

- confirm `release.config.cjs` sets `branches: ["release"]`
- confirm there is no semantic-release publishing branch configured for `main`
- confirm the release workflow triggers from `release`
- confirm PR-title validation runs on PRs to `main`
- confirm `release.config.cjs` includes `@semantic-release/changelog`,
  `@semantic-release/git`, `@semantic-release/github`, and
  `@semantic-release/exec`

### Merge Policy Checks

- confirm repository settings require squash merge to `main`
- confirm direct pushes to `main` are blocked
- confirm promotion from `main` to `release` is done by merge or fast-forward,
  not squash
- confirm the release bot can push only the changelog commit it needs to `release`

### Release Behavior Checks

- create a `fix:` PR to `main`, promote to `release`, and verify a patch release
  tag is created
- create a `feat:` PR to `main`, promote to `release`, and verify a minor
  release tag is created
- create a breaking-change PR to `main`, promote to `release`, and verify a
  major release tag is created
- confirm each release creates or updates:
  - a GitHub Release
  - `CHANGELOG.md`
- confirm each release produces:
  - one immutable Git tag `vX.Y.Z`
  - one immutable `ui:vX.Y.Z` image tag
  - one immutable `backend:vX.Y.Z` image tag
  - one commit-SHA image tag for each image
- confirm the release manifest `git_sha` matches the commit referenced by
  `git rev-list -n 1 vX.Y.Z`
- confirm the Docker/CI workflow uses the semantic-release version for both image
  tags and the release manifest

### Example Checks

```bash
sed -n '1,240p' release.config.cjs
sed -n '1,240p' commitlint.config.cjs
sed -n '1,260p' .github/workflows/release.yml
sed -n '1,220p' .github/workflows/semantic-pr-title.yml
sed -n '1,220p' CHANGELOG.md
git tag --sort=-v:refname | head
```

## Summary

The required semantic-release policy for this repo is:

- use semantic-release as the only version authority
- publish only from `release`
- enforce conventional-commit intent at the `main` boundary via PR titles
- squash-merge PRs into `main`
- promote `main` into `release` without squash
- let semantic-release create immutable tags, GitHub releases, and a generated
  `CHANGELOG.md`
- publish immutable container tags derived from the semantic-release version and
  released commit SHA
- do not commit version bumps back into the repository
