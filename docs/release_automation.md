# Release Automation

Read [AGENTS.md](../AGENTS.md) and
[specs/deploy/subspecs/40_release_please_and_commit_policy.md](../specs/deploy/subspecs/40_release_please_and_commit_policy.md)
first.

## Canonical Flow

The repository no longer uses a long-lived `release` branch.

The intended release path is:

1. releasable work lands on `main` with conventional-commit PR titles
2. `release-please` runs on pushes to `main` and maintains one draft release PR
   against `main`
3. merging that release PR lets `release-please` create the immutable Git tag
   and GitHub release
4. the published GitHub release triggers `Release Publish`, which builds both
   container images, writes `release-manifest.json`, and uploads that manifest
   to the GitHub release
5. `Release Publish` then calls `Release Deploy`, which rolls the tagged release
   onto ECS using only immutable published artifacts

Manual redeploys stay on the same immutable contract:

- dispatch `Release Deploy`
- provide the published release tag
- let the workflow download that tag's `release-manifest.json` and redeploy it

## GitHub Settings

Two repository settings matter:

- `RELEASE_PLEASE_TOKEN` must be configured so release-please-created tags and
  releases can trigger downstream workflows
- GitHub Actions must be allowed to create pull requests

## Validation Guardrails

Release workflow changes should fail before merge when they introduce invalid
inline shell. The repository now treats GitHub workflow linting as part of the
normal quality gate:

- `make tidy` runs `make workflow-lint`
- `PR CI` runs `actionlint` with `shellcheck` support before the other lanes

That guard exists specifically to catch workflow-shell parsing bugs such as
indented heredocs inside `run:` blocks before they break a published release.

## AWS OIDC Subjects

The Terraform-owned release and deploy roles should allow GitHub OIDC subjects
for:

- `refs/heads/main` for release preparation and manual redeploys
- `refs/tags/v*` for publish and deploy runs driven by immutable GitHub release
  tags

The old `refs/heads/release` trust shape is obsolete.
