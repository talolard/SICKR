# Release Branch Governance

Read [AGENTS.md](../AGENTS.md) and
[specs/deploy/subspecs/40_release_please_and_commit_policy.md](../specs/deploy/subspecs/40_release_please_and_commit_policy.md)
first.

## Purpose

The repository cannot declare GitHub branch protection in source, but it can
still make the intended `main -> release` boundary explicit and auditable.

This repo now owns two workflow checks:

- `Release PR Governance`: only allow PRs into `release` from `main` promotion
  or a Release Please head ref
- `Release Branch Governance`: audit each push to `release` and reject anything
  that is neither:
  - a history-preserving promotion from `main`
  - a release-please metadata commit that only updates release files

These checks are not a substitute for GitHub branch rules. They are the
mechanical checks that branch rules should require.

## Required GitHub Rule For `release`

Configure the GitHub branch rule for `release` to require:

- pull requests before merging
- no force pushes
- `Release PR Governance / Validate release PR governance` as a required status
  check
- direct push access restricted as tightly as possible

The repo cannot enforce those settings itself, so keep this document aligned
with the actual GitHub rule.

## Allowed Paths

Normal allowed updates to `release` are:

- a PR from `main` that preserves history into `release`
- a Release Please PR whose head ref starts with
  `release-please--branches--release`

Disallowed updates include:

- direct hotfix commits on `release`
- feature branches merged directly into `release`
- cherry-picks from `main` that rewrite commit identity instead of preserving
  history

## Emergency Exception

If Tal must push directly to `release` during recovery, treat that as a
documented exception.

After the incident:

- write down why the branch rule was bypassed
- restore the intended `main -> release` flow
- remove the exceptional commit from future steady-state guidance if it should
  not be repeated
