# Synthesized Deployment Review And Revised Recommendation

This document merges the two critique notes and incorporates the inline comments
left in both.

This is the canonical top-level deployment spec for the near-term public
deployment.
The focused specs in
[subspecs/](./subspecs/) decompose this document into implementation-facing
areas.
Read [subspecs/00_context.md](./subspecs/00_context.md) before reading the
individual subspecs.

Branching rule:
- start all deployment-project implementation from `tal/deployproject` or from
  a stacked branch that descends from it

## Comment Checklist

- [x] CloudFront/CDN and TLS: switched the public-edge recommendation to
  `CloudFront + ACM`, and called out that streaming paths need special handling.
- [x] CloudFront plus SSE concern: kept CloudFront, but made `/ag-ui/*`
  streaming validation an explicit deployment requirement.
- [x] Do not turn this into a full Terraform spec yet: kept infra details
  intentionally high level and moved exact AWS resource design to a deferred
  section.
- [x] Aurora Serverless v2 should scale to `0`: made scale-to-zero the intended
  operating mode for this low-duty-cycle deployment.
- [x] Close connections after 15 minutes: added
  `idle_session_timeout = 15 minutes` as part of the database plan.
- [x] Clarify why `idle_session_timeout` matters: explained that it helps drain
  idle sessions so Aurora can pause, but app-side connection behavior still has
  to cooperate.
- [x] Keep `RDS Proxy` out for this use case: made it an explicit non-goal for
  this deployment.
- [x] Use the latest Aurora PostgreSQL version: updated the recommendation to
  "latest Aurora PostgreSQL version that supports the required `pgvector`
  extension."
- [x] Drop the "Terraform later" critique for now: removed that as a core issue
  since a dedicated Terraform spec will follow separately.
- [x] Pick the `main -> release` promotion model if a `release` branch exists:
  made that the recommended branch model.
- [x] Release tooling should now be explicit: selected `release-please` for
  release PR preparation, changelog generation, and version-file updates, while
  keeping final publication gated on built and pushed artifacts plus a release
  manifest.
- [x] Ignore Helm/commit-SHA conventions for this repo: omitted that line of
  critique from the synthesis.
- [x] Split static product images from dynamic attachments: added a public image
  bucket and a separate private runtime-artifacts bucket.
- [x] Product images should be public: routed them through CloudFront-backed
  public URLs.
- [x] Attachments should be private: kept them in private storage with fresh
  presigned access at read time rather than durable public URLs.
- [x] Use an AWS-managed secret store: recommended AWS Secrets Manager at a high
  level, without specifying the exact injection mechanism yet.
- [x] Domain is a future subdomain of `talperry.com`: captured that as the
  expected public DNS shape.
- [x] Keep AWS detail minimal for now: reduced the infra prerequisites to a
  short operational contract.
- [x] Single-instance risk is acceptable for this friend-sharing phase: stated
  that explicitly.

## Scope

This is not the Terraform spec and not the final AWS resource design. The goal
here is narrower:

- correct the routing and deployment picture
- turn the overlapping critiques into one coherent recommendation
- make the key decisions explicit
- leave low-value infrastructure detail deferred

## Revised Recommendation

### 1. Deployment Shape

Use this near-term topology:

- one `CloudFront` distribution as the public edge
- one ACM certificate attached to CloudFront
- one public app domain on a subdomain of `talperry.com`, specifically
  `designagent.talperry.com`
- one small EC2 host as the application origin
- `nginx` on that EC2 host as the reverse proxy to local containers
- one `ui` container running Next.js
- one `backend` container running FastAPI + PydanticAI + AG-UI
- Aurora Serverless v2 PostgreSQL
- one public S3 bucket for product images
- one private S3 bucket for attachments and generated runtime artifacts

This keeps the current application architecture intact while making the public
edge, storage policy, and deployment path more coherent.

### 2. Public Routing Model

The biggest correction from the earlier recommendation is this:

- many browser-visible routes are still owned by the Next.js app, even when they
  proxy to the backend behind the scenes
- only the AG-UI transport should go directly to the backend

Recommended public routing:

| Public path | Public origin target | Notes |
| --- | --- | --- |
| `/`, app pages, `/_next/*` | `ui` via `nginx` | Normal Next.js app traffic |
| `/api/copilotkit` | `ui` via `nginx` | CopilotKit runtime route lives in Next.js |
| `/api/attachments` | `ui` via `nginx` | Next.js route currently handles attachment upload proxying |
| `/attachments/*` | `ui` via `nginx` | Keep browser contract stable even if reads later resolve to presigned URLs |
| `/api/thread-data/*` | `ui` via `nginx` | Next.js route proxies backend thread APIs |
| `/api/agents*` | `ui` via `nginx` | Next.js route proxies backend metadata APIs |
| `/api/traces*` | `ui` via `nginx` | Keep disabled in production-like deploys for now |
| `/ag-ui/*` | `backend` via `nginx` | Direct AG-UI SSE transport path |
| `/static/product-images/*` | CloudFront S3 image origin | Cacheable public image path |

That preserves one public app domain while keeping the current same-origin
browser assumptions for the application itself.

### 3. Edge, CDN, And TLS

Use `CloudFront` as the public edge and TLS termination layer.

Recommended CloudFront behaviors:

- default app behavior forwards to the EC2 app origin and should be effectively
  non-cacheing for dynamic app traffic
- `/ag-ui/*` uses a dedicated dynamic behavior with caching disabled and
  streaming validated end to end
- `/static/product-images/*` uses the S3 image origin with normal CDN caching

Important note for AG-UI:

- `/ag-ui/*` streams SSE responses
- CloudFront forwards requests to custom origins over HTTP/1.1
- CloudFront supports `Transfer-Encoding: chunked`, which is the response shape
  that matters most for streaming
- CloudFront's origin response timeout is effectively also the maximum allowed
  gap between response packets
- for `POST` requests, if the origin stops responding for longer than that read
  timeout, CloudFront drops the connection and does not retry
- the CloudFront plus `nginx` path must therefore be configured and tested so
  streaming is not buffered or broken
- the `/ag-ui/*` behavior should use caching disabled, and its timeout settings
  must be chosen with long-lived streaming in mind
- this is not a nice-to-have; it is a launch gate

This lets CloudFront handle the public certificate and static image delivery
while keeping `nginx` as the simple application origin and local reverse proxy.

### 4. Database

Use Aurora Serverless v2 PostgreSQL, on the latest Aurora PostgreSQL version
that supports the required `pgvector` extension.

Near-term database policy:

- commit to Serverless v2 auto-pause down to `0` ACU for this deployment
- do not use `RDS Proxy`
- set `idle_session_timeout = 15 minutes`
- keep application connections from lingering indefinitely

Why the timeout matters:

- Aurora can only pause when idle sessions are actually gone
- `idle_session_timeout` helps by draining old idle sessions
- that does not remove the need for application-side connection discipline

So the deployed runtime should use a connection strategy that is intentionally
pause-friendly. Start with conservative pooling. If the current pooled engine
prevents reliable pause-to-zero, switch the deployed runtime to `NullPool`.

The acceptance criteria for this database choice should be:

- the cluster reliably returns to `0` ACU after inactivity
- the first request after idle is allowed to be slow, but succeeds cleanly
- the UI or app path tolerates cold-wake latency without looking broken

### 5. Storage

The storage story should be split by artifact family, not treated as one generic
"files on S3" decision.

#### Product Images

Product images are static and should be public.

Recommended shape:

- store them in a dedicated public S3 bucket
- front that bucket with CloudFront
- expose them at `/static/product-images/*` on the app domain
- use `IMAGE_SERVING_STRATEGY=direct_public_url` in deployed environments
- seed `public_url` values to the CloudFront-backed image URLs

That removes unnecessary backend proxy load and matches the static access
pattern.

#### Attachments And Generated Runtime Artifacts

Attachments and generated artifacts are dynamic and should stay private.

Recommended shape:

- store them in a separate private S3 bucket
- keep stable attachment or artifact IDs in durable state
- do not store raw expiring presigned URLs as the durable contract
- resolve reads to fresh presigned GET URLs, or redirect to them, at request time

This keeps the privacy boundary correct without forcing the transcript state to
depend on expiring URLs.

#### Trace Bundles

Trace bundles should remain disabled in production-like deployments for now. The
current trace-reporting flow is developer-oriented and does not need to be part
of the first public rollout.

### 6. Release And Deployment Model

Use one application-level version per deployable release, and release the `ui`
and `backend` together.

Recommended branch and release model:

- `main` remains the normal integration branch
- `release` is the promotion branch
- changes move from `main` to `release`
- do not merge feature branches directly into `release`

Recommended artifact model:

- publish `ui` and `backend` images to ECR
- deploy by exact immutable version tags or digests
- keep one app-level semver per release

Recommended deploy flow:

1. merge feature work into `main` with conventional-commit-style PR titles and
   squash merge so the resulting `main` history carries release intent
2. promote validated `main` commits into `release` without squashing away the
   commit history that release tooling must analyze
3. `release-please` creates or updates a draft release PR on `release`
4. merging that release PR updates `CHANGELOG.md` and `version.txt` on
   `release`
5. publish automation builds and pushes both `ui` and `backend` images to ECR
6. publish automation writes the release manifest and records the exact image
   digests
7. only after both images exist and the manifest exists do we create the
   immutable Git tag and GitHub release
8. CI then triggers an SSM-based deploy on the EC2 host
9. the host pulls the exact pinned image references and runs
   `docker compose up -d`

Release-note behavior should be split clearly:

- `release-please` is responsible for the reviewed in-repo changelog and
  version-file update
- the final GitHub release is created only after artifact publication and may
  generate GitHub-native release notes from the immutable tag at that point

Auth and publication gates should also stay explicit:

- if the default GitHub token is insufficient for the desired release-please
  PR behavior, `RELEASE_PLEASE_TOKEN` is a Tal-owned gate
- image publication requires the repository variable `AWS_RELEASE_ROLE_ARN` so
  GitHub Actions can assume the AWS publish role by OIDC
- a release is not considered published until both images are built, pushed,
  tagged with the release version, and captured in the release manifest

### 7. Minimum Operational Contract

These are the minimum non-negotiable operational pieces, without trying to
fully spec AWS:

- CloudFront + ACM for public TLS
- a stable app domain on a subdomain of `talperry.com`
- a stable origin path from CloudFront to the EC2 app host
- AWS-managed secrets for database, model-provider, and observability credentials
- `PY_AG_UI_URL` and similar app wiring set correctly between `ui` and `backend`
- EC2 instance access for ECR pulls, S3 access, and SSM management
- lightweight health checks before the first real deploy
- a migration and bootstrap step that prepares schema plus required seeded data
- basic observability for app logs and runtime traces

For secrets, the recommendation is:

- use AWS Secrets Manager at a high level
- do not commit production `.env` files
- do not bury secrets inside image builds

For database/bootstrap, the recommendation is:

- deployment must include schema migration
- deployment must also include initialization of required catalog, embedding, and
  image metadata before the app serves live traffic
- the exact production bootstrap mechanism is deferred

### 8. Explicitly Accepted Tradeoffs

This deployment is intentionally optimized for low fixed cost and easy sharing,
not high availability.

Accepted tradeoffs:

- one EC2 host is a single point of failure
- deployments may briefly brown out traffic unless the deploy script is careful
- Aurora cold wakes are acceptable if the app handles them cleanly
- we are choosing simplicity over a heavier platform move right now

That is acceptable for this phase because the goal is to share the app with
friends and gather real feedback, not to present a production-grade uptime
story.

## Deferred Details

The following are intentionally deferred to the next layer of planning:

- Terraform module and resource layout
- exact AWS account and region wiring
- VPC, subnet, and security-group specifics
- exact secret-injection mechanism
- exact `nginx` config blocks
- exact health endpoint contracts
- exact migration/bootstrap implementation
- rollback runbook details
- future refinements to branch protection and release-please workflow policy

## Bottom Line

The corrected near-term picture is:

- CloudFront as the public edge and TLS layer
- one EC2 app origin with `nginx`, `ui`, and `backend`
- direct backend routing only for `/ag-ui/*`
- product images served publicly from a separate S3 + CloudFront path
- private attachments and generated artifacts stored separately with presigned
  read access
- Aurora Serverless v2 PostgreSQL, latest supported `pgvector`-capable version,
  explicitly tuned for pause-to-zero
- a simple `main -> release` promotion flow with `release-please`,
  manifest-backed artifact publication, and SSM-based deployment

That is a more cohesive and correct deployment recommendation than the current
doc, without pretending we have already finished the Terraform or AWS
implementation details.
