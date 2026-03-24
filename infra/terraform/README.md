# Terraform Deployment Scaffold

This directory is the Terraform source of truth for the deployment surface
described in `specs/deploy/`.

Current scope:

- one AWS account: `046673074482`
- primary region: `eu-central-1`
- secondary provider alias only for CloudFront ACM: `us-east-1`
- one `dev` environment root
- provider/tagging/state/account guardrails
- hosted-zone discovery for `talperry.com`

This scaffold intentionally does not provision the full deployment yet.
Its job is to lock the root layout and the provider/state contract so later
Terraform work lands into a stable structure instead of reinventing it.

## Layout

```text
infra/terraform/
  README.md
  environments/
    dev/
      backend.tf
      main.tf
      outputs.tf
      providers.tf
      terraform.tfvars.example
      variables.tf
      versions.tf
```

## Normal Workflow

Use Tal's personal AWS context:

```bash
export AWS_DEFAULT_PROFILE=tal
export AWS_REGION=eu-central-1
```

Then run:

```bash
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev validate
terraform -chdir=infra/terraform/environments/dev plan
terraform -chdir=infra/terraform/environments/dev output -json
```

## Hosted Zone Strategy

The existing `talperry.com` public hosted zone is not created by this stack.
The environment root discovers it as a data source and later Terraform work
will create the deployment records inside that existing zone.

That keeps the bootstrap simple:

- no one-time manual import is required just to read the hosted zone
- later record resources still remain Terraform-managed
- account and region guardrails stay explicit from the first commit

## Next Steps

Later tasks should add resources in this order:

1. IAM, Secrets Manager, and ECR
2. VPC, EC2 host, and origin DNS
3. Aurora and S3 buckets
4. CloudFront, ACM, and public DNS
