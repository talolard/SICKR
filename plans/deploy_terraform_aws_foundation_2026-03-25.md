# Deploy Terraform AWS Foundation Plan

Date: 2026-03-25
Epic: `tal_maria_ikea-v9b.4`
Branch: `epic/tal_maria_ikea-v9b.4-deployment-terraform-and-aws-foundation`

## Why

The current Terraform tree already covers the shared foundation for state,
providers, tags, IAM, ECR, and Secrets Manager.
This epic finishes the AWS substrate needed by the deployment spec without
restarting the layout from scratch.

The source of truth for this work is:

- `specs/deploy/guiding_principles.md`
- `specs/deploy/final_deployment_recommendation_2026-03-24_synthesized.md`
- `specs/deploy/multi_agent_review.md`
- `specs/deploy/subspecs/00_context.md`
- `specs/deploy/subspecs/20_terraform_aws_setup.md`
- `specs/deploy/subspecs/50_edge_and_app_routing.md`

## Scope

In scope:

- network substrate in `eu-central-1`
- single EC2 origin host with SSM posture and origin DNS
- Aurora Serverless v2 cluster with pause-friendly parameter groups
- product-image and private-artifact buckets
- CloudFront, ACM in `us-east-1`, and public DNS on `talperry.com`
- Terraform outputs and docs that expose the deploy contract

Out of scope:

- application logic changes
- release workflow changes
- host-local deployment orchestration beyond minimal instance bootstrap
- taking over the full `talperry.com` hosted zone as a Terraform-managed zone

## Design Decisions

### Build forward from the existing environment root

Keep `infra/terraform/environments/dev` as the composition root and preserve
the existing identity, registry, and secret resources.
Add thin deployment-specific modules only for the newly introduced AWS
surfaces:

- `modules/network`
- `modules/compute`
- `modules/database`
- `modules/storage`
- `modules/edge`

This matches the spec direction without refactoring the already-landed shared
foundation.

### Keep the hosted zone as discovered shared infrastructure

`talperry.com` already exists and contains unrelated DNS state.
The environment root should continue to discover the hosted zone as a data
source rather than try to recreate or fully import the zone resource.

Terraform should manage only the deployment records it owns:

- `designagent.talperry.com`
- `origin.designagent.talperry.com`
- ACM validation records for the viewer certificate

Where an equivalent record may already exist manually, use Route53 record
resources with overwrite-safe posture so the first apply can adopt the record
without broad zone ownership.

### Keep the EC2 host simple and SSM-first

Provision one small x86_64 EC2 instance in a public subnet, attach the existing
runtime instance profile, give it an Elastic IP, and attach the origin record.
Bootstrap only the baseline packages and writable paths needed by later deploy
automation.

Do not add SSH ingress by default.
SSM remains the first-line host access path.

### Keep CloudFront explicit about route families

The distribution should encode only the three required behavior families:

- default dynamic app traffic
- `/ag-ui/*` streaming traffic
- `/static/product-images/*` static product images

Product images should use a private bucket plus CloudFront OAC.
Dynamic routes should keep caching disabled and preserve request state needed by
the existing same-origin Next.js and AG-UI contract.

## Validation Plan

Primary validation:

- `terraform fmt -recursive infra/terraform`
- `terraform -chdir=infra/terraform/environments/dev init -backend=false`
- `terraform -chdir=infra/terraform/environments/dev validate`
- `terraform -chdir=infra/terraform/environments/dev init`
- `terraform -chdir=infra/terraform/environments/dev plan -var-file=terraform.tfvars -lock=false -refresh=false`

Live-account note:

- use `AWS_PROFILE=tal`, `AWS_DEFAULT_PROFILE=tal`, and `AWS_REGION=eu-central-1`
- if Terraform or the S3 backend needs fully resolved credentials, run
  `eval "$(aws configure export-credentials --profile tal --format env)"`
- targeted `aws` checks for Route53, ACM, CloudFront, RDS, and S3 remain useful
  follow-up validation once the environment values are in place

This branch no longer treats live-account validation as blocked on an expired
session. The current expectation is that contributors validate against the real
AWS account with the `tal` profile or exported credentials before calling the
Terraform slice ready.
