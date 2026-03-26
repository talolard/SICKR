# Terraform And AWS Setup

Read [00_context.md](./00_context.md) first for the shared goals and
deployment assumptions.
Read [25_ecs_fargate_alb_runtime.md](./25_ecs_fargate_alb_runtime.md) for the
runtime-specific decision.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

## Decision

We should manage the long-lived AWS deployment surface with Terraform.

For this deployment phase, the Terraform-managed target is:

- one AWS account: `046673074482`
- one primary region: `eu-central-1`
- one public app domain under `talperry.com`
- one CloudFront distribution in front of the app
- one public ALB as the app origin
- one ECS cluster with two Fargate services
- one Aurora PostgreSQL Serverless v2 cluster with pause-to-zero enabled
- one public image bucket and one private runtime-artifacts bucket
- two ECR repositories: one for `ui`, one for `backend`

This is intentionally not a generalized multi-account platform.

## Non-Goals

This spec does not aim to provide:

- Kubernetes
- a generalized multi-environment platform abstraction
- a fully hardened production edge posture
- a full DR and backup playbook
- a reusable company-wide Terraform module library

The point is to make the current app deployable, cheap enough, and automatable
without changing the product architecture.

## Concrete AWS Baseline

The near-term AWS baseline should be:

- account `046673074482`
- primary region `eu-central-1`
- Route53 authoritative DNS for `talperry.com`
- one deployment environment root, initially `dev`
- one application subdomain, supplied by variable, under `talperry.com`

Recommended v1 domain shape:

- public app hostname: `designagent.talperry.com`
- public CloudFront alias: `designagent.talperry.com`

There is no separate origin-host DNS contract anymore. CloudFront should use
the ALB DNS name directly as the app origin.

## Terraform Source Of Truth

Terraform should be the source of truth for deployment infrastructure.

That means:

- durable AWS deployment resources are created and changed by Terraform
- CI and deploy automation consume Terraform outputs instead of rediscovering
  infrastructure ad hoc
- manual console changes are allowed only for bootstrapping secret values and
  for emergency recovery

Current implementation honesty note:

- Terraform already exports the ECS cluster and service names, ALB DNS name,
  CloudFront distribution, bucket names, and GitHub role ARNs
- the current deploy workflows still use live AWS API discovery for service
  baselines and ALB-derived runtime details
- that rediscovery is implementation debt, not the intended steady-state
  contract

## Repository Layout

Recommended Terraform layout:

```text
infra/terraform/
  README.md
  bootstrap/
    state/
  modules/
    database/
    edge/
    identity/
    network/
    registry/
    runtime/
    storage/
  environments/
    dev/
```

Rules for this layout:

- `bootstrap/state` creates the remote-state bucket and nothing else
- `environments/dev` composes the deployment from local modules
- modules remain thin and deployment-specific rather than trying to be generic

## State Management

Use remote Terraform state in S3.

Recommended backend posture:

- backend bucket in `eu-central-1`
- bucket versioning enabled
- default encryption enabled
- one state key per environment root
- `use_lockfile = true`
- `allowed_account_ids = ["046673074482"]`

Do not use DynamoDB locking for new implementation work.

## Provider Shape

Use one primary AWS provider and one explicit alias for `us-east-1`.

Provider intent:

- `aws` handles normal deployment resources in `eu-central-1`
- `aws.us_east_1` handles the ACM certificate that CloudFront presents to
  viewers

Reason for the `us-east-1` exception:

- AWS requires ACM certificates attached to CloudFront viewer traffic to be
  requested or imported in `us-east-1`

## Naming And Tagging

Tagging should be mandatory and mostly provider-driven.

Required provider-level tags:

- `Project = tal-maria-ikea`
- `Service = ikea-agent`
- `Environment = dev`
- `ManagedBy = terraform`
- `Repository = talolard/SICKR`
- `Owner = tal`

Required resource-level tags where applicable:

- `Name`
- `Component`
- `Role`
- `DataClassification`

## Network Shape

The near-term network should be:

- one small dedicated VPC
- two public subnets across two AZs
- two database subnets across two AZs
- no NAT gateway

Security groups should be:

- `alb_sg`
  - allow inbound HTTP `80` from the internet
- `ui_service_sg`
  - allow inbound `3000` only from `alb_sg`
- `backend_service_sg`
  - allow inbound `8000` only from `alb_sg`
- `database_sg`
  - allow inbound PostgreSQL `5432` only from `backend_service_sg`

The Fargate tasks should run in the public subnets with public IPs enabled.
That is an explicit v1 tradeoff to avoid NAT and keep the architecture smaller.

Optional hardening later:

- keep the ALB internet-facing for CloudFront, but restrict forwarding to
  requests that include a CloudFront-added secret origin header

## Runtime Shape

Terraform should provision:

- one internet-facing ALB
- one ECS cluster
- one `ui` target group and service
- one `backend` target group and service
- one task-definition family per service
- one CloudWatch log group per service
- task execution and task roles

The services should start with:

- placeholder task definitions
- `desired_count = 0`
- `lifecycle.ignore_changes = [task_definition, desired_count]`

That lets CI own rollout revisions without Terraform fighting the deployed task
definition.

## ALB Contract

The ALB should:

- listen on HTTP `80`
- default to the `ui` target group
- route `/ag-ui/*` to the `backend` target group

Health check paths:

- `ui` target group: `/api/health/live`
- `backend` target group: `/api/health/live`

## CloudFront Contract

Terraform should manage the public edge for the app hostname.

Required CloudFront behavior split:

- default `*` -> ALB origin, effectively non-cacheing
- `/ag-ui/*` -> same ALB origin, non-cacheing and streaming-safe
- `/static/product-images/*` -> S3 image origin with long-lived caching

## Database

Use Aurora Serverless v2 PostgreSQL, on the latest Aurora PostgreSQL version
that supports the required `pgvector` extension.

Policy:

- pause-to-zero enabled
- `idle_session_timeout = 15 minutes`
- `idle_in_transaction_session_timeout = 1 minute`
- no `RDS Proxy`

## Storage

Terraform should provision:

- one public product-image bucket
- one private runtime-artifacts bucket

The public image bucket should remain private at the bucket-policy level and be
readable only through CloudFront origin access control.

## IAM

Terraform should provision:

- GitHub OIDC provider
- release-publish role for image publication
- deploy role for ECS rollout automation
- Terraform apply role
- ECS task execution role
- backend task role
- UI task role

The deploy role should be able to:

- describe services and task definitions
- register task definitions
- run one-off ECS tasks
- update ECS services
- pass the ECS task roles needed by those operations

It should not depend on EC2 or SSM permissions.

## GitHub Repository Variables

Terraform outputs should be sufficient to populate these repo variables:

- `AWS_RELEASE_ROLE_ARN`
- `AWS_DEPLOY_ROLE_ARN`
- `ECS_CLUSTER_NAME`
- `ECS_BACKEND_SERVICE_NAME`
- `ECS_UI_SERVICE_NAME`
- `IKEA_IMAGE_CATALOG_RUN_ID`

The release and deploy IAM roles must trust GitHub OIDC subjects from both
`refs/heads/release` and `refs/heads/main` today because the repo still contains
the transitional `manual-ref-deploy` workflow.

Target posture:

- the canonical publish/deploy path should run from `release`
- the extra `main` trust should be removed when the manual source-ref deploy
  lane is deleted

The old EC2-targeting repo variables are obsolete:

- `DEPLOY_TARGET_TAG_KEY`
- `DEPLOY_TARGET_TAG_VALUE`

## Redundant Old Surface

The following Terraform surfaces are obsolete under this spec:

- EC2 app host
- Elastic IP for the app host
- origin Route53 record for the app host
- instance profile for a runtime host
- SSM-managed deploy target discovery

## Verification

Useful verification for this subspec includes:

- `terraform fmt -recursive infra/terraform`
- `terraform -chdir=infra/terraform/environments/dev init -backend=false`
- `terraform -chdir=infra/terraform/environments/dev validate`
- confirming outputs include the ECS cluster and service names, ALB DNS name,
  CloudFront distribution, Aurora endpoint, and bucket names
