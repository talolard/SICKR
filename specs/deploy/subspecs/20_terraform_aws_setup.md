# Terraform And AWS Setup

Read [00_context.md](./00_context.md) first for the shared goals and
deployment assumptions.

Implementation branch rule:
- start work for this subspec from `tal/deployproject` or from a stacked branch
  that descends from it

This subspec defines the Terraform and AWS shape for the near-term deployment.
It is intentionally prescriptive: it picks a concrete v1 instead of leaving the
major deployment questions open.

## Decision

We should manage the long-lived AWS deployment surface with Terraform.

For this deployment phase, the Terraform-managed target is:

- one AWS account: `046673074482`
- one primary region: `eu-central-1`
- one public app domain under `talperry.com`
- one CloudFront distribution in front of the app
- one small single-host app origin
- no required host-level reverse proxy layer
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

The point is to make the current app deployable, cheap, and automatable without
changing the product architecture.

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
- origin hostname: `origin.designagent.talperry.com`

`origin.designagent.talperry.com` should be a Route53 record managed by Terraform and
used only as the CloudFront custom origin hostname.

## Terraform Source Of Truth

Terraform should be the source of truth for deployment infrastructure.

That means:

- durable AWS deployment resources are created and changed by Terraform
- CI and deploy automation consume Terraform outputs instead of rediscovering
  infrastructure ad hoc
- manual console changes are allowed only for bootstrapping secret values and
  for emergency recovery

When the Terraform tree is implemented, it should include:

- `infra/terraform/README.md` explaining the architecture, state layout, and
  normal commands
- repo docs that point deployment readers to the Terraform tree
- an `AGENTS.md` update stating that Terraform is the source of truth for
  deployment infrastructure

## Repository Layout

Recommended Terraform layout:

```text
infra/terraform/
  README.md
  bootstrap/
    state/
  modules/
    compute/
    database/
    edge/
    identity/
    network/
    registry/
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
The current Terraform S3 backend supports S3 lockfiles directly, and
DynamoDB-based locking is deprecated.

Recommended backend shape:

```hcl
terraform {
  backend "s3" {
    bucket              = "tal-maria-ikea-terraform-state-046673074482-eu-central-1"
    key                 = "deploy/dev/terraform.tfstate"
    region              = "eu-central-1"
    use_lockfile        = true
    allowed_account_ids = ["046673074482"]
  }
}
```

Bootstrap rule:

- the state bucket is created by a separate bootstrap root before the main
  environment root is initialized

## Provider Shape

Use one primary AWS provider and one explicit alias for `us-east-1`.

Recommended provider posture:

```hcl
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region              = "eu-central-1"
  allowed_account_ids = ["046673074482"]

  default_tags {
    tags = local.default_tags
  }
}

provider "aws" {
  alias               = "us_east_1"
  region              = "us-east-1"
  allowed_account_ids = ["046673074482"]

  default_tags {
    tags = local.default_tags
  }
}
```

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

Expected `DataClassification` values:

- `public` for public edge resources and the product-image bucket
- `private` for the database, private bucket, and secrets
- `internal` for CI and deployment plumbing

Naming convention:

- use `ikea-agent` as the shared service prefix for AWS resource names where
  AWS naming rules allow it
- include `dev` in environment-scoped names
- include account id in S3 bucket names because S3 names are globally unique

Examples:

- `ikea-agent-dev-vpc`
- `ikea-agent-dev-db`
- `ikea-agent/ui`
- `ikea-agent/backend`
- `ikea-agent-dev-046673074482-product-images`
- `ikea-agent-dev-046673074482-private-artifacts`

## Networking

Use a small dedicated VPC.

Required v1 network shape:

- one VPC
- two public subnets across two AZs
- two private database subnets across two AZs
- one internet gateway
- public route table for app-host subnets
- private route tables for database subnets
- no NAT gateway

Why no NAT gateway in v1:

- the app host can live in a public subnet
- Aurora stays private
- avoiding NAT saves steady-state cost and complexity

Required security groups:

- `app_host_sg`
  - allow inbound traffic on the `ui` origin port and the `backend` origin port
  - if practical, prefer restricting those ports to CloudFront-origin traffic;
    if not, document the broader ingress as an explicit v1 tradeoff
  - allow all egress
- `db_sg`
  - allow inbound PostgreSQL `5432` only from `app_host_sg`
  - no public ingress

This spec does not attempt origin hardening beyond that baseline.
If we later want to restrict origin access to CloudFront-only traffic, that
should be a focused edge-hardening follow-up.

Viewer-routing rule:

- `designagent.talperry.com` is the only supported browser entrypoint
- `origin.designagent.talperry.com` exists only so CloudFront has a stable custom-origin
  hostname for the `ui` and `backend` origins
- direct user traffic to the origin hostname is out of contract even if the
  host remains internet-reachable in v1

## Compute

Terraform should provision one small EC2 application host in `eu-central-1`.

Required compute posture:

- one EC2 instance in a public subnet
- one Elastic IP attached to the instance
- one Route53 record for `origin.designagent.talperry.com` pointing at that Elastic IP
- one instance profile with the runtime IAM permissions defined below

Terraform owns:

- the instance
- the instance profile
- the security group
- the Elastic IP
- the Route53 origin record

Terraform does not own:

- image builds
- host-local application code checkout
- ad hoc SSH deploy scripting

Current SSH posture note:

- keep the optional EC2 key-pair variable for now because SSH is an allowed
  fallback in principle
- do not treat it as an active v1 access path because the current network
  posture does not open inbound port `22`
- if fallback SSH becomes operationally necessary later, add that change
  intentionally rather than assuming the key-pair variable already enables it

The Dockerization and CI/CD subspec defines the release artifacts and deploy
contract.

## Database

Use Aurora PostgreSQL Serverless v2 in `eu-central-1`.

This is not just an AWS preference.
It is specifically chosen so the low-duty-cycle deployment can pause to zero
when idle and resume on demand.

Required database posture:

- engine: `aurora-postgresql`
- engine mode compatible with Serverless v2
- one writer instance class `db.serverless`
- private DB subnet group
- private security group
- storage encryption enabled
- backup retention set to `7` days
- no `RDS Proxy`

Required scaling posture:

- `min_capacity = 0`
- `max_capacity = 2`
- `seconds_until_auto_pause = 900`

Rationale:

- `min_capacity = 0` is what turns on pause-to-zero
- `seconds_until_auto_pause = 900` gives a 15-minute idle window before pausing
- `max_capacity = 2` is enough for a low-volume friend-facing deployment and
  can be raised later without changing the overall architecture

Recommended Terraform shape:

```hcl
resource "aws_rds_cluster" "main" {
  cluster_identifier = "ikea-agent-dev-db"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  storage_encrypted  = true
  backup_retention_period = 7

  serverlessv2_scaling_configuration {
    min_capacity             = 0
    max_capacity             = 2
    seconds_until_auto_pause = 900
  }
}
```

Terraform must also provision custom parameter groups for the idle-connection
policy that supports auto-pause.

Required idle-session policy:

- set `idle_session_timeout = 900000`

Recommended additional protection:

- set `idle_in_transaction_session_timeout = 60000`

Reason for these values:

- `idle_session_timeout = 900000` terminates idle non-transaction sessions after
  15 minutes so they do not keep the cluster warm indefinitely
- `idle_in_transaction_session_timeout = 60000` avoids silently keeping broken
  transactions open for long periods, without making normal short transactions
  fragile

Important scope detail:

- `idle_session_timeout` is a PostgreSQL engine parameter and belongs in the
  DB instance parameter group managed by Terraform

`pgvector` should be enabled through migrations or bootstrap SQL, not by trying
to solve extension lifecycle inside Terraform.

## Object Storage

Terraform should provision two separate S3 buckets because they solve different
problems.

### Product Images Bucket

Required posture:

- bucket name pattern:
  `ikea-agent-dev-046673074482-product-images`
- block direct public bucket access
- enable default encryption
- enable versioning
- let CloudFront access the bucket through Origin Access Control
- treat object keys as immutable

Terraform should manage:

- the bucket
- public access block
- versioning
- encryption
- bucket policy allowing the CloudFront distribution to read objects
- the CloudFront Origin Access Control

This matches the decision in
[10_cloudfront_product_images.md](./10_cloudfront_product_images.md).

### Private Artifacts Bucket

Required posture:

- bucket name pattern:
  `ikea-agent-dev-046673074482-private-artifacts`
- block all public access
- enable default encryption
- enable versioning
- grant access only to the runtime role
- add a simple lifecycle rule to expire incomplete multipart uploads

This bucket is for:

- attachments
- generated runtime artifacts
- any private file output needed by the app

## Edge, TLS, And DNS

Terraform should manage the public edge for the app hostname.

Required edge posture:

- Route53 record for `designagent.talperry.com`
- Route53 record for `origin.designagent.talperry.com`
- one CloudFront distribution with alias `designagent.talperry.com`
- one ACM certificate in `us-east-1` for `designagent.talperry.com`
- Route53 validation records for that certificate

Required CloudFront behavior split:

- default behavior -> the `ui` custom origin at `origin.designagent.talperry.com`
  on the UI host port
- ordered behavior `/ag-ui/*` -> the `backend` custom origin at
  `origin.designagent.talperry.com` on the backend host port, with caching
  disabled and streaming-safe request/response posture
- ordered behavior `/static/product-images/*` -> S3 product-image origin

Required origin-port contract:

- UI origin port: `3000`
- backend origin port: `8000`

Required image behavior posture:

- cache `GET` and `HEAD`
- do not forward cookies
- do not forward authorization state
- do not vary on query strings
- use long TTLs because product-image object keys are immutable

Required app-origin behavior posture:

- forward the methods needed by the app's dynamic routes
- disable caching for dynamic app traffic
- keep the default behavior simple and compatible with the existing Next.js
  route ownership

Required AG-UI behavior posture:

- path pattern `/ag-ui/*`
- target the backend custom origin rather than the UI origin
- disable caching
- allow `POST`
- forward the request details needed for streaming transport
- tune origin-request and response timeouts for long-lived SSE

The certificate must be created in `us-east-1` because CloudFront requires ACM
viewer certificates to be requested or imported there.

This spec still defers:

- WAF
- CloudFront origin restrictions stronger than the baseline SG
- final CloudFront timeout tuning for SSE-heavy routes

## Container Registry

Terraform should provision exactly two ECR repositories:

- `ikea-agent/ui`
- `ikea-agent/backend`

Required ECR posture:

- `image_tag_mutability = IMMUTABLE`
- `scan_on_push = true`
- lifecycle policy to keep recent tagged releases and prune old untagged images
- repository URIs exported as Terraform outputs

Suggested lifecycle rule:

- keep the most recent `50` tagged images
- aggressively expire untagged images

Terraform does not build or push images.
It only provides the registry and IAM contract around it.

## IAM

Terraform should create four IAM roles or role groupings.

### 1. Runtime Role

Attached to the EC2 app host.

Required permissions:

- pull from the two ECR repositories
- read required Secrets Manager secrets
- read and write the private artifacts bucket
- read the product-image bucket only if a maintenance path needs it
- use SSM core instance management

### 2. GitHub Actions Build Role

Assumed through GitHub OIDC.

Required permissions:

- authenticate to ECR
- push images to `ikea-agent/ui` and `ikea-agent/backend`
- read Terraform outputs or deployment metadata if needed by the workflow

This role should not apply Terraform.

### 3. GitHub Actions Deploy Role

Assumed through GitHub OIDC.

Required permissions:

- read the release manifest or explicit image references
- identify the target EC2 instance
- use SSM to trigger deployment on that instance
- read deployment-relevant Terraform outputs

This role should not have broad infrastructure-admin permissions.

### 4. Terraform Apply Role

Used by a human or tightly controlled automation for Terraform plan/apply.

Required permissions:

- create and update the AWS resources in this spec
- no permissions outside account `046673074482` and the specified scope

## Secrets

Terraform should create secret containers, not commit secret values.

Required secret objects:

- one secret for backend application/runtime configuration
- one secret for model-provider credentials
- one secret for observability credentials if needed
- one database connection secret, unless the final implementation reuses an
  AWS-managed database secret directly

Recommended secret naming:

- `tal-maria-ikea/dev/backend-app`
- `tal-maria-ikea/dev/model-providers`
- `tal-maria-ikea/dev/observability`
- `tal-maria-ikea/dev/database`

Near-term bootstrap process:

- Terraform creates the Secrets Manager secret objects and exposes their names
  or ARNs as outputs
- initial values are populated manually in AWS Secrets Manager during
  environment bootstrap
- the runtime role reads those secrets at container start or deploy time
- secret rotation updates Secrets Manager values rather than rebuilding images

## Required Outputs

Terraform must expose the values that CI/CD and operators need.

Required outputs:

- AWS account id
- app domain
- origin domain
- CloudFront distribution id
- CloudFront domain name
- ACM certificate ARN
- product-image bucket name
- private-artifacts bucket name
- `ui` ECR repository URI
- `backend` ECR repository URI
- database endpoint
- database port
- database secret ARN
- app-host instance id
- app-host public IP
- secret ARNs for runtime configuration

These outputs are the contract boundary between Terraform and the Dockerization
and CI/CD subspec.

## Explicit Deferrals

This spec intentionally does not decide:

- the exact EC2 instance type and AMI
- blue/green or canary rollout patterns
- WAF and advanced edge hardening
- exact CloudWatch alarm set and dashboard layout
- final CloudFront timeout tuning for AG-UI streaming
- backup retention beyond the v1 minimum
- a second environment beyond `dev`

Those details should be added only when they materially improve this
deployment.

## Goal Compliance

This spec complies with the deployment goals in [00_context.md](./00_context.md)
if the implementation preserves all of the following:

- **Current architecture stays intact**
  - the app still deploys as separate `ui` and `backend` services
  - product images move to CloudFront-backed direct URLs without changing the UI
    contract
  - the current route ownership split remains valid
- **Cheap and simple first public deployment**
  - one app host
  - one small VPC
  - no NAT gateway
  - no Kubernetes
  - Aurora pause-to-zero enabled
- **Coherent automation**
  - Terraform owns infrastructure
  - CI consumes Terraform outputs
  - CI deploys immutable container artifacts instead of source code
- **No broad rewrites for hosting**
  - no product rewrite
  - no GitOps platform
  - no new application-layer routing model

## Verification Procedure

When this spec is implemented, verify it against the goals with the following
checks.

### Terraform Structure Checks

- confirm `infra/terraform/README.md` exists and explains the normal workflow
- confirm the environment root is `infra/terraform/environments/dev`
- confirm the backend uses S3 with `use_lockfile = true`
- confirm Terraform is restricted to account `046673074482`

Suggested verification commands:

```bash
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev validate
terraform -chdir=infra/terraform/environments/dev plan
terraform -chdir=infra/terraform/environments/dev output -json
```

Example checks:

```bash
rg -n "use_lockfile\\s*=\\s*true|allowed_account_ids" infra/terraform
sed -n '1,220p' infra/terraform/README.md
```

### AWS Resource Checks

- confirm the primary resources are in `eu-central-1`
- confirm the ACM certificate used by CloudFront is in `us-east-1`
- confirm Route53 contains `designagent.talperry.com` and `origin.designagent.talperry.com`
- confirm CloudFront has:
  - a default app-origin behavior
  - an ordered `/ag-ui/*` behavior
  - an ordered `/static/product-images/*` behavior
- confirm the product-image bucket is not public and is readable through OAC
- confirm the private-artifacts bucket blocks all public access
- confirm the database cluster has:
  - `MinCapacity = 0`
  - `MaxCapacity = 2`
  - `SecondsUntilAutoPause = 900`
- confirm the DB instance parameter group sets:
  - `idle_session_timeout = 900000`

Suggested verification commands:

```bash
aws --region eu-central-1 rds describe-db-clusters \
  --db-cluster-identifier ikea-agent-dev-db

aws --region us-east-1 acm list-certificates

aws ecr describe-repositories \
  --region eu-central-1 \
  --repository-names ikea-agent/ui ikea-agent/backend
```

For Route53 and CloudFront, verify by checking:

- the alias records in the `talperry.com` hosted zone
- the CloudFront distribution behaviors for the default origin and
  `/static/product-images/*`
- the S3 bucket policy on the product-image bucket to confirm CloudFront OAC
  access rather than public bucket access

Example checks:

```bash
aws --region us-east-1 acm list-certificates
aws --region us-east-1 acm describe-certificate --certificate-arn <cert-arn>
aws --region eu-central-1 route53 list-resource-record-sets --hosted-zone-id <zone-id>
aws cloudfront get-distribution --id <distribution-id>
aws --region eu-central-1 rds describe-db-clusters --db-cluster-identifier ikea-agent-dev-db
aws --region eu-central-1 rds describe-db-parameters --db-parameter-group-name <db-parameter-group> \
  --query "Parameters[?ParameterName=='idle_session_timeout' || ParameterName=='idle_in_transaction_session_timeout'].[ParameterName,ParameterValue]"
```

### Operational Contract Checks

- confirm Terraform outputs include the ECR repository URIs, DB endpoint, secret
  ARNs, and CloudFront identifiers
- confirm the ECR repositories are named `ikea-agent/ui` and
  `ikea-agent/backend`
- confirm ECR tag mutability is immutable
- confirm the runtime role can read secrets and the private bucket but cannot
  mutate unrelated AWS resources
- confirm the build role can push images but cannot apply Terraform
- confirm the deploy role can trigger deployment but does not have broad admin
  privileges

Example checks:

```bash
terraform -chdir=infra/terraform/environments/dev output
aws --region eu-central-1 ecr describe-repositories --repository-names ikea-agent/ui ikea-agent/backend
aws iam get-role --role-name <runtime-role-name>
aws iam get-role --role-name <github-build-role-name>
aws iam get-role --role-name <github-deploy-role-name>
```

### Goal-Level Checks

- confirm there is still only one app host and no NAT gateway
- confirm product images are served from the CloudFront path on the same app
  hostname
- confirm a release can be deployed using Terraform outputs plus pinned image
  references, with no host-local image build step

Operational verification method:

- run Terraform and collect outputs
- use those outputs as the only AWS identifiers consumed by CI and deploy
- confirm the release workflow can deploy by image digest and Terraform outputs
  alone
- confirm that no deploy step checks out source code on the host in order to
  rebuild the app

Example checks:

```bash
curl -I https://designagent.talperry.com/static/product-images/<known-object-key>
terraform -chdir=infra/terraform/environments/dev output ui_ecr_repository_uri
terraform -chdir=infra/terraform/environments/dev output backend_ecr_repository_uri
```

## Summary

The Terraform and AWS shape for this deployment should be:

- account `046673074482`
- primary region `eu-central-1`
- `us-east-1` provider alias only for the CloudFront viewer certificate
- Route53-managed subdomain under `talperry.com`
- S3 remote state with S3 lockfiles, not DynamoDB locking
- one small VPC and one EC2 app host with an Elastic IP
- Aurora PostgreSQL Serverless v2 configured explicitly for pause-to-zero
- idle session timeouts managed in Terraform parameter groups
- separate public-image and private-artifact buckets
- one CloudFront distribution with same-host product-image routing
- one dedicated CloudFront behavior for `/ag-ui/*` streaming traffic
- two ECR repos named `ikea-agent/ui` and `ikea-agent/backend`
- IAM and Secrets Manager shaped around runtime, build, deploy, and Terraform
  apply roles
