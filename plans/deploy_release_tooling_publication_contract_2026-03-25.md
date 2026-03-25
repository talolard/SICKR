# Deployment Release Tooling And Publication Contract Plan

Date: 2026-03-25

## Goal

Finish epic `tal_maria_ikea-v9b.1` by making the deployment release-policy
surface internally consistent and implementation-ready.

The result should let later workflow work consume one clear contract for:

- branch roles
- release PR behavior
- changelog and release-note generation
- auth and human gates
- artifact publication and final release publication

## Scope

- `specs/deploy/final_deployment_recommendation_2026-03-24_synthesized.md`
- `specs/deploy/multi_agent_review.md`
- `specs/deploy/subspecs/00_context.md`
- `specs/deploy/subspecs/30_dockerization_and_cicd.md`
- `specs/deploy/subspecs/40_*_commit_policy.md`
- release-policy helper config or adjacent docs only where they materially
  define the contract

Out of scope:

- implementing or rewriting GitHub workflow jobs
- changing deploy runtime behavior outside the documented release contract
- Terraform, host bootstrap, or runtime bootstrap implementation

## Decisions To Encode

1. `release-please` is the chosen release-preparation tool.
2. `main` is the integration branch and `release` is the promotion and publish
   branch.
3. PRs into `main` carry conventional-commit intent through title enforcement
   and squash merge.
4. Promotion from `main` to `release` must preserve the releasable commit
   history that `release-please` analyzes.
5. `release-please` owns release PR preparation plus `CHANGELOG.md` and
   `version.txt` updates; it does not by itself publish the release.
6. A release is published only after both container images are built, pushed,
   tagged with the release version, and captured in the release manifest.
7. The immutable Git tag and GitHub release happen after artifact publication,
   not before.
8. The optional `RELEASE_PLEASE_TOKEN` and required `AWS_RELEASE_ROLE_ARN`
   remain explicit gates rather than hidden assumptions.

## Deliverables

- top-level deploy spec updated to reflect the chosen release flow
- review doc updated so it no longer points at a stale semantic-release plan
- release subspec renamed and/or rewritten so the file name and content match
  `release-please`
- Docker/CI contract updated to describe final publication sequencing and
  release-note behavior clearly

## Validation

- review the edited spec set for one consistent definition of "published
  release"
- validate helper config and manifest scripts only where the docs depend on
  their current behavior
- run broader repo validation only if the touched surface crosses into
  formatter/lint/test-enforced implementation files
