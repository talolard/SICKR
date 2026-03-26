# Terraform Deployment Infrastructure

This directory is the Terraform source of truth for the deployment surface
described in `specs/deploy/`.

Current scope:

- one AWS account: `046673074482`
- primary region: `eu-central-1`
- secondary provider alias only for CloudFront ACM: `us-east-1`
- one `dev` environment root
- provider, tagging, state, and account guardrails
- hosted-zone discovery for `talperry.com`
- GitHub OIDC provider for Actions
- shared IAM roles for release publication, deploy, and Terraform apply
- ECR repositories for `ui` and `backend`
- Secrets Manager containers for runtime config, model providers, observability,
  and database access
- one dedicated deployment VPC with public runtime subnets and private DB subnets
- one public ALB
- one ECS cluster with two Fargate services
- one Aurora PostgreSQL Serverless v2 cluster with pause-friendly parameter groups
- one product-image bucket and one private-artifacts bucket
- one CloudFront distribution, viewer ACM certificate, and public DNS alias

The Route53 hosted zone for `talperry.com` remains shared infrastructure that is
discovered as a data source. Terraform manages only the deployment-owned
records inside that zone:

- `designagent.talperry.com`
- viewer-certificate validation records

That keeps the deployment records in Terraform without taking ownership of the
entire apex zone and its unrelated DNS state.

## Layout

```text
infra/terraform/
  README.md
  bootstrap/
    state/
      main.tf
      outputs.tf
      providers.tf
      versions.tf
  modules/
    database/
    edge/
    network/
    runtime/
    storage/
  environments/
    dev/
      backend.tf
      database.tf
      edge.tf
      identity.tf
      locals.tf
      main.tf
      network.tf
      outputs.tf
      providers.tf
      registry.tf
      runtime.tf
      secrets.tf
      storage.tf
      terraform.tfvars.example
      variables.tf
      versions.tf
```

## Normal Workflow

Use Tal's personal AWS context:

```bash
export AWS_DEFAULT_PROFILE=tal
export AWS_PROFILE=tal
export AWS_REGION=eu-central-1
```

If the local profile resolves to short-lived credentials, export the resolved
session into the current shell before a live `init` or `plan` so Terraform, the
S3 backend, and the AWS provider all use the same identity:

```bash
eval "$(aws configure export-credentials --profile tal --format env)"
```

Then run:

```bash
terraform -chdir=infra/terraform/bootstrap/state init
terraform -chdir=infra/terraform/bootstrap/state apply
terraform -chdir=infra/terraform/environments/dev init -backend=false
terraform -chdir=infra/terraform/environments/dev validate
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev plan -var-file=terraform.tfvars
terraform -chdir=infra/terraform/environments/dev output -json
```

## Hosted Zone Strategy

The existing `talperry.com` public hosted zone is not created by this stack.
The environment root discovers it as a data source and creates only the
deployment-owned records inside that existing zone.

That keeps the bootstrap simple:

- no risky full-zone import is required just to read the hosted zone
- deployment-owned records still remain Terraform-managed
- `allow_overwrite = true` lets the first apply adopt an existing manual record
  for the same name if one is already present
- account and region guardrails stay explicit from the first commit

## Deploy Topology

The `dev` environment root composes five thin modules:

- `network`: VPC, subnets, route tables, and security groups
- `runtime`: ALB, ECS cluster, task definitions, services, log groups, and
  task IAM roles
- `database`: Aurora Serverless v2 and the pause-friendly parameter group
- `storage`: product-image and private-artifact S3 buckets
- `edge`: CloudFront, `us-east-1` ACM, validation records, and public aliases

Network posture inside that root stays explicit:

- the ALB and Fargate tasks live in public subnets
- each database subnet gets an explicit private route table with no internet
  route
- there is no NAT gateway in v1

The CloudFront distribution encodes the required routing split from the deploy
spec:

- default behavior for the ALB app origin
- `/ag-ui/*` as the streaming-sensitive dynamic behavior, also zero-cache
- `/static/product-images/*` as the S3-backed image behavior

The ECS runtime stays intentionally simple:

- one public ALB
- one ECS cluster
- one `ui` Fargate service and one `backend` Fargate service
- placeholder task definitions with `desired_count = 0` until CI performs the
  first real rollout
- no EC2 host, no user data, no SSM rollout target, and no required `nginx`
  layer
- public IPs on the tasks as an explicit v1 tradeoff to avoid NAT and keep the
  network surface small

CloudFront uses the ALB DNS name directly as the only application origin.
The ALB listener owns the HTTP route split:

- default `*` -> `ui` target group
- `/ag-ui/*` -> `backend` target group

## Outputs

The environment root exports the identifiers that release automation and manual
operators need:

- GitHub Actions OIDC provider ARN
- ECR repository names and URIs
- Secrets Manager secret names and ARNs
- release-publish, deploy, and Terraform-apply role ARNs
- product-image and private-artifact bucket names and ARNs
- ECS cluster name
- ECS backend and UI service names
- ALB DNS name
- Aurora endpoint, port, and master-secret ARN
- CloudFront distribution id, ARN, domain name, and viewer certificate ARN

The release workflow should use the `release_publish_role_arn` output for the
repository variable `AWS_RELEASE_ROLE_ARN`. The role trust policy should allow
GitHub OIDC subjects from `refs/heads/release`, because release publication and
redeploys are driven by immutable published releases rather than source-ref
builds from `main`.

The deploy workflow should use:

- `ecs_cluster_name`
- `ecs_backend_service_name`
- `ecs_ui_service_name`
- `cloudfront_distribution_id` only if a later deploy step truly needs targeted
  invalidation
- the secret ARNs from Terraform outputs rather than rediscovering them in AWS

## Validation

Useful local validation for this tree is:

```bash
terraform -chdir=infra/terraform/environments/dev init -backend=false
terraform -chdir=infra/terraform/environments/dev validate
terraform fmt -recursive infra/terraform
```

Useful live-account validation is:

```bash
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev plan -var-file=terraform.tfvars -lock=false -refresh=false
terraform -chdir=infra/terraform/environments/dev output
```

The exact PR `#95` head has already completed a live remote-backend `init` and
`plan` with exported credentials from the `tal` profile. Treat that exported
credential path as the current operator workflow, not as a pending future
validation step.
