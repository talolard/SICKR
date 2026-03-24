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
- GitHub OIDC provider for Actions
- shared IAM roles for runtime, release publication, deploy, and Terraform apply
- ECR repositories for `ui` and `backend`
- Secrets Manager containers for runtime config, model providers, observability,
  and database access

This root intentionally stops at the shared foundation.
It does not yet provision the VPC, EC2 host, Aurora cluster, S3 buckets, or
CloudFront distribution.

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
  environments/
    dev/
      backend.tf
      identity.tf
      locals.tf
      main.tf
      outputs.tf
      providers.tf
      registry.tf
      secrets.tf
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
terraform -chdir=infra/terraform/bootstrap/state init
terraform -chdir=infra/terraform/bootstrap/state apply
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

## Shared Foundation Outputs

The environment root now exports the identifiers that release automation needs
before the rest of the AWS stack exists:

- GitHub Actions OIDC provider ARN
- ECR repository names and URIs
- Secrets Manager secret names and ARNs
- runtime, release-publish, deploy, and Terraform-apply role ARNs
- reserved bucket names for product images and private artifacts

The release workflow should use the `release_publish_role_arn` output for the
repository variable `AWS_RELEASE_ROLE_ARN`.

## Next Steps

Later tasks should add resources in this order:

1. VPC, EC2 host, and origin DNS
2. Aurora and S3 buckets
3. CloudFront, ACM, and public DNS
