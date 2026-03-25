# ECS Fargate And ALB Runtime

This subspec defines the canonical managed application-runtime shape for the
deployment project.

Read [00_context.md](./00_context.md) first for the shared goals and high-level
deployment decisions.
Read [20_terraform_aws_setup.md](./20_terraform_aws_setup.md) for the broader
AWS surface.
Read [30_dockerization_and_cicd.md](./30_dockerization_and_cicd.md) for the
release and rollout contract.
Read [50_edge_and_app_routing.md](./50_edge_and_app_routing.md) for the public
route split.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

The application runtime should be:

- one public ALB
- one ECS cluster
- one `backend` ECS Fargate service
- one `ui` ECS Fargate service
- one CloudFront distribution in front of the ALB and the product-image bucket

This replaces the older single-EC2-host deploy model.

## Why This Is Better For This Project

This project optimizes for:

- simple automation
- low operational burden
- predictable, repeatable deploys
- easy debugging without nursing a host

For those goals, the Fargate+ALB model is better because it deletes an entire
class of operational work:

- no host bootstrap scripts
- no host package drift
- no host-local compose orchestration
- no SSM command payload layer
- no host-local rollback state

The downside is steady-state cost: Fargate does not naturally give us
application scale-to-zero the way Aurora Serverless v2 does for the database.
That trade is acceptable here because simplicity is more important than shaving
the last amount of infra cost from the always-on app tier.

## Canonical Topology

The canonical public topology is:

- `CloudFront`
- `ALB`
- `ui` Fargate service
- `backend` Fargate service
- `Aurora Serverless v2`
- public product-image bucket
- private artifacts bucket

Route ownership:

- CloudFront handles the public hostname and CDN edge
- ALB handles app HTTP path routing
- ECS runs the two application containers

## ALB Responsibilities

The ALB should own the final HTTP route split for app traffic:

- `/ag-ui/*` -> `backend` target group
- default `*` -> `ui` target group

This is simpler than trying to keep multiple application origins behind
CloudFront and it removes the need for a reverse-proxy container or host-local
proxy.

## CloudFront Responsibilities

CloudFront should stay in front because we still want:

- the public viewer certificate
- one public hostname
- a stable image CDN path on the same host
- path-specific cache policy on `/static/product-images/*`
- path-specific no-cache behavior on `/ag-ui/*`

CloudFront should therefore use:

- default behavior -> ALB origin
- `/ag-ui/*` behavior -> same ALB origin with no cache and streaming-safe
  settings
- `/static/product-images/*` behavior -> S3 image origin

## ECS Runtime Responsibilities

The ECS runtime should be intentionally small:

- one cluster
- one task-definition family for `ui`
- one task-definition family for `backend`
- one service per family
- CloudWatch log groups for both
- task execution role plus task roles

Terraform should create the stable baseline task definitions with placeholder
images and `desired_count = 0`.
CI should register new task-definition revisions and scale/update the services.

That keeps Terraform responsible for the static runtime contract and CI
responsible for release rollouts.

## Networking Posture

To avoid NAT and additional moving parts in v1:

- use public subnets for the ALB
- use the same public subnets for the Fargate tasks
- assign public IPs to the Fargate tasks
- do not allow internet ingress directly to the task security groups
- allow ingress only from the ALB security group
- keep Aurora in separate database subnets with ingress only from the backend
  task security group

This is a deliberate simplicity-over-hardening choice for the side-project
phase.

Optional hardening later:

- if direct ALB access becomes a concern, keep CloudFront in front and restrict
  the ALB to requests that contain a CloudFront-added secret origin header

## Internal Backend URL

The UI task should call the backend through the ALB path split, not through
Docker-local networking and not through Cloud Map in v1.

Required runtime value:

- `PY_AG_UI_URL=http://<alb-dns>/ag-ui/`

This is one extra hop, but it avoids adding service discovery just to let the
UI call the backend.

## One-Off Tasks

The deploy system still needs one-off backend tasks for:

- migrations
- seed verification

Those should run as ECS Fargate tasks using the freshly registered backend
task-definition revision before the backend service is updated.

Environment bootstrap remains separate and is not part of every release deploy.

## Redundant Old Path

The following surfaces are redundant under this design and should not be kept
alive as parallel deployment options:

- EC2 app host
- origin-host Route53 record for the app
- host-level `docker compose` deploy
- SSM deploy workflow
- host-bundle rendering scripts
- host-local rollback state

## Pre-Deploy Work Still Required

Moving to this architecture does not make the system instantly launch-ready.
The remaining concrete work before first real deploy is:

1. Terraform must provision the ECS cluster, ALB, services, task roles, and
   CloudFront-to-ALB origin wiring.
2. The release and deploy workflows must target ECS instead of EC2.
3. The one-off database bootstrap must still happen for the environment.
4. Product images must still be present in S3 before public launch, even though
   the app shell can deploy earlier.

## Validation

Useful validation for this runtime shape includes:

- `terraform validate` on the runtime module
- local tests for ECS task-definition rendering
- one successful Fargate migration task
- one successful Fargate seed-verification task
- one successful ECS service rollout for both `backend` and `ui`
- one public-path validation on `designagent.talperry.com`
