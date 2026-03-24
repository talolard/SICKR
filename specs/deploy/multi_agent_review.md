# Multi-Agent Review

This document summarizes four independent planning passes over the canonical
deployment spec and its subspecs.

Parent spec:
- [final_deployment_recommendation_2026-03-24_synthesized.md](./final_deployment_recommendation_2026-03-24_synthesized.md)

Subspec context:
- [subspecs/00_context.md](./subspecs/00_context.md)

Guiding principles:
- [guiding_principles.md](./guiding_principles.md)

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it

## Purpose

The goal of this review is to extract:

- likely implementation epics and tasks
- the dependency structure between them
- what is probably on the critical path
- where the planners agreed
- where they disagreed
- which unknowns still need human decisions

## Agent 1: Runtime-First

Core thesis:
- execute from the application contract outward, not from Terraform inward

Main recommendations:
- freeze route ownership, runtime config, health/readiness, and AG-UI streaming
  behavior first
- finalize product-image and private-attachment contracts before bucket/IAM work
- define migration/bootstrap and Aurora pause-friendly DB behavior before final
  deploy orchestration
- let Terraform, CI/CD, and release automation consume those contracts

Critical-path emphasis:
- `R1 -> R2 -> R3 -> R4 -> S1/S2 -> S3 -> S4 -> S5 -> P1 -> P2/P3 + I2/I3/I4 -> I5 -> L2 -> L3 -> L4`

Biggest risks:
- AG-UI stream cadence may be too weak for CloudFront and `nginx`
- current DB pooling may prevent Aurora pause-to-zero
- seed/bootstrap may be heavier than expected
- generated artifacts may not all already fit the stable attachment contract

## Agent 2: CI/Release-First

Core thesis:
- freeze the release authority and artifact contract first, then prove image
  builds before any publishing, then prove origin deploy before public-edge
  complexity

Main recommendations:
- finalize `main -> release`, immutable tags/digests, released-commit identity,
  and release manifest semantics early
- build release tooling and Docker pipeline early
- treat the first reliable deploy-to-origin as the main milestone
- add CloudFront/public edge only after origin deploy works

Critical-path emphasis:
- release authority
- Docker/image publication
- minimal deploy target and host bootstrap
- deploy orchestration and readiness
- public-edge/storage verification gates

Biggest risks:
- ambiguity around Aurora bootstrap source
- UI image may not be as environment-reusable as assumed
- branch protection/bot permissions may block release automation late

## Agent 3: Infra-First

Core thesis:
- prove the origin stack first, then add CloudFront, then automate release and
  publish

Main recommendations:
- freeze the few decisions that would cause late infra churn
- stand up Terraform state and the AWS substrate early
- build the origin runtime/bootstrap path next
- make the app compatible with the target infra shape before public edge
- keep release automation important but not on the first launch critical path

Critical-path emphasis:
- deployment contracts
- Terraform core substrate
- origin runtime bootstrap
- app storage/readiness integration
- edge cutover

Biggest risks:
- CloudFront SSE behavior
- Aurora pause-to-zero under the real runtime connection pattern
- product-image seeding may be more work than it looks
- DNS ownership or Terraform control of `talperry.com` may not be as assumed

## Agent 4: Risk-First

Core thesis:
- treat this as a proof-first rollout, not an infra-first rollout

Main recommendations:
- run early validation spikes for:
  - AG-UI streaming through `CloudFront -> nginx -> backend`
  - Aurora Serverless v2 pause-to-zero and cold wake with the real app pattern
- rehearse deploy-time commands manually before relying on CI/CD
- add explicit health/readiness and deterministic migration/bootstrap entrypoints
- only finalize CloudFront and launch once rehearsal and rollback are proven

Critical-path emphasis:
- proof spikes and decision freeze
- app deployability contract
- Terraform foundation using the spike results
- artifact build and deploy automation
- observability, rehearsal, and launch gates

Biggest risks:
- SSE through CloudFront may force design changes, not just tuning
- Aurora pause-to-zero may force runtime and Terraform changes
- semver automation may distract from launch readiness if treated as mandatory
- secret injection and product-image `public_url` seeding remain operational
  dependencies

## Cross-Agent Consistencies

Strong agreement across the four planners:

- do not combine first-time infra bring-up, first-time app bootstrap, and
  first-time CloudFront/SSE debugging in one cutover
- prove the real public-path deploy behavior before launch
- freeze route ownership, config contract, health/readiness, and storage
  contracts early
- treat AG-UI streaming and Aurora pause-to-zero as the two biggest technical
  unknowns
- make deploy success depend on:
  - pinned images
  - migration
  - bootstrap/seed verification
  - backend readiness
  - UI readiness
  - one end-to-end app check
- keep release-tool choice from blocking higher-risk runtime validation work
  where possible

## Cross-Agent Tensions

There are two real tensions in the plans:

### 1. What comes first: release contract or runtime proof

- the CI/release-first plan wants release authority and artifact semantics
  frozen first
- the runtime-first and risk-first plans want SSE and Aurora proof work first

Current recommendation:
- prioritize runtime proof and deployability contracts first
- keep the release/artifact contract close behind, but not ahead of the two
  largest technical risks

### 2. Semver tooling status

- the top-level synthesized deployment spec still treats semver tooling choice
  as deferred
- [subspecs/40_semantic_release_and_commit_policy.md](./subspecs/40_semantic_release_and_commit_policy.md)
  already selects `semantic-release`

Current recommendation:
- replace the semantic-release-specific plan with a release-please-based release
  automation plan
- do not let release-tool choice block higher-risk runtime validation work

## Aggregated Recommendation

The best current synthesis is a six-phase plan.

Important planning context from the human owner:

- this is a single-developer project
- repeatable and correct automation is preferred over a one-off fast launch path
- full release and deploy automation should be treated as an important project
  goal before the app is shown externally

### Phase 1: Decision Freeze And Proof Spikes

- freeze the small set of cross-cutting deployment decisions
- run an AG-UI streaming proof through the intended path
- run an Aurora pause-to-zero and cold-wake proof with the real app behavior
- rehearse deploy-time commands manually outside CI/CD

### Phase 2: Application Deployability Contract

- explicit backend liveness/readiness
- explicit UI readiness through `PY_AG_UI_URL`
- deterministic migration/bootstrap entrypoints
- Aurora-friendly runtime connection behavior
- private S3 attachments and generated artifacts
- deployed product-image `direct_public_url` mode and seeding
- deploy-safe runtime flags and minimum observability

### Phase 3: Terraform Foundation

- remote state, providers, tagging, outputs
- ECR, IAM/OIDC, Secrets Manager
- VPC/subnets/SGs, EC2 origin host
- Aurora
- S3 buckets
- only after streaming proof: CloudFront/ACM and the real `/ag-ui/*` behavior

### Phase 4: Images And Host Deploy Contract

- production Dockerfiles
- host runtime contract with `docker compose`
- env/secrets injection
- pinned digest consumption
- host deploy runner

### Phase 5: Release And Deploy Automation

- release manifest generation/consumption
- image build/publish workflow
- deploy workflow via SSM
- rollback-by-previous-manifest
- release-please / PR-title enforcement if not already landed

### Phase 6: Rehearsal And Launch

- prove full stack through the intended public hostname
  `designagent.talperry.com`
- run one dress rehearsal including idle wake and rollback
- require one rollback manifest and a short operator runbook before launch

## Recommended Critical Path

Recommended high-level critical path:

1. freeze key decisions
2. prove SSE and Aurora assumptions
3. make the app deployable
4. stand up Terraform substrate
5. build images and deploy runner
6. prove end-to-end deploy through the intended public path
7. run dress rehearsal
8. launch

Short form:

`decision freeze -> SSE/Aurora spikes -> health/bootstrap/storage contracts -> Terraform core -> Docker + deploy runner -> public-path validation -> dress rehearsal -> launch`

## Open Decisions For Interview

No unresolved high-level interview decisions remain at this stage.
The next step is to turn the answered decisions into final epics and tasks.

## Interview Updates

### Decision 1: Automation Priority

Answer:
- full release and deploy automation should be in place and correct before the
  first real external-facing deployment
- repeatability is more important than optimizing for the fastest possible first
  launch

Planning impact:
- release automation moves onto the critical path
- release tooling, manifest generation, image publication, and deploy
  orchestration should not be treated as optional polish
- origin-only manual deployment rehearsals may still be useful as internal proof
  steps, but they are no longer considered sufficient as the main path to first
  launch

### Decision 2: DNS And Route53 Ownership

Answer:
- the relevant hosted zone is `talperry.com`
- the relevant public hosted zone already exists in AWS account `046673074482`
- Terraform in this repo should manage the deployment DNS records there
- importing existing Route53 resources at the beginning is acceptable if it
  simplifies ongoing management

Planning impact:
- Route53 control is confirmed, so DNS does not need to be modeled as an
  external/manual dependency
- Terraform import/setup for the existing hosted zone should be treated as an
  early infrastructure task
- the AWS foundation and edge-cutover phases can assume in-account DNS control
  once the exact zone name is confirmed

### Decision 3: Initial Secret Bootstrap Ownership

Answer:
- Tal will manually populate the initial secret values in AWS Secrets Manager
  after Terraform creates the secret containers
- this should be represented later as an explicit human-owned gate in the task
  plan

Planning impact:
- Terraform should create secret containers and outputs, but not try to own the
  secret values
- release/deploy automation must depend on a human-complete bootstrap gate for
  initial secret population
- the final task plan should include an explicit Tal-owned checkpoint before the
  first real deploy rehearsal

### Decision 4: Uploads And Generated Artifacts

Answer:
- uploads and generated runtime artifacts are in first-launch scope

Planning impact:
- private S3-backed attachment and generated-artifact storage remains on the
  critical path
- stable `/api/attachments` and `/attachments/{id}` browser behavior must be
  validated before launch
- artifact retrieval and privacy boundaries must be part of dress rehearsal and
  launch gates

### Decision 5: Release Tool Preference

Answer:
- prefer `release-please` over `semantic-release`
- if `release-please` requires a Tal-provided GitHub token or bot credential for
  the desired workflow, add an explicit Tal-owned gate for that input
- a release is not considered published until both containers are built, pushed,
  tagged with the release version, and the release manifest exists

Planning impact:
- the current semantic-release-specific subspec is now stale and should be
  replaced by a release-please-oriented release-tooling spec
- release automation remains critical, but its implementation should favor a
  more reviewable release-PR-centered model
- the task plan should include a conditional Tal-owned credential/bootstrap gate
  if the default GitHub token is insufficient
- release preparation and release publication should be split:
  - release-please prepares the release change
  - image build/push and manifest publication happen before final release
    publication
- final immutable tagging/publication must happen only after artifact creation
  succeeds

### Decision 6: Public Hostname And Deploy Path

Answer:
- the public hostname should be `designagent.talperry.com`
- the corresponding origin hostname should be `origin.designagent.talperry.com`
- do not make origin-only rehearsal a required milestone before the first real
  end-to-end deploy through the intended public path

Planning impact:
- all deploy docs and Terraform naming should use `designagent.talperry.com`
  rather than `app.talperry.com`
- origin-path checks may still exist as internal validation, but they are not
  the primary success milestone
- the launch-critical validation path should match the final public hostname and
  route behavior

### Decision 7: Database Bootstrap Strategy

Answer:
- for the first deployed environment, use the current seed/verify path rather
  than introducing a new restore-based bootstrap mechanism immediately
- later, optimize bootstrap with a reusable pre-seeded database/template
  approach rather than making first-launch depend on snapshot restore

Planning impact:
- the first implementation should package the existing migration + seed/verify
  flow into a deterministic deploy step
- restore-based acceleration is a later optimization, not a prerequisite for the
  first launch
- the bootstrap contract should be written so a future pre-seeded database path
  can replace or accelerate the slow path without changing the deploy interface

### Decision 8: Product-Image Launch Requirement

Answer:
- direct public product-image delivery is mandatory before launch
- backend-proxy image serving is not an acceptable launch fallback
- the image corpus is large enough that baking it into containers or serving it
  repeatedly through the backend is operationally the wrong shape

Planning impact:
- product-image bucket population, immutable object keys, and seeded
  `public_url` values stay on the critical path
- the launch checklist must include successful direct image delivery from the
  bucket/CDN path
- backend image proxying may remain in the codebase for local development and
  fallback scenarios, but not as the intended deployed public path
