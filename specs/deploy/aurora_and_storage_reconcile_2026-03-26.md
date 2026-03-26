# Aurora And Storage Reconcile

Date: 2026-03-26
Task: `tal_maria_ikea-v9b.4.4`

## Purpose

This note records the current evidence that the repository and live AWS account
already match the intended low-cost Aurora plus S3 storage posture for the
deployment project.

The task is no longer a greenfield provisioning exercise. The useful work here
is to prove that the Terraform contract and the live account agree on the
database and storage resources that later deploy automation depends on.

## Terraform Contract

The current Terraform tree already encodes the required posture.

Database contract:

- `infra/terraform/modules/database/main.tf`
  - Aurora PostgreSQL Serverless v2 cluster
  - `serverlessv2_scaling_configuration`
    - `min_capacity = var.min_capacity`
    - `max_capacity = var.max_capacity`
    - `seconds_until_auto_pause = var.seconds_until_auto_pause`
  - instance parameter group with:
    - `idle_session_timeout = 900000`
    - `idle_in_transaction_session_timeout = 60000`
- `infra/terraform/environments/dev/database.tf`
  - wires the environment root to the shared database module
- `infra/terraform/environments/dev/terraform.tfvars.example`
  - `database_min_capacity = 0`
  - `database_max_capacity = 2`
  - `database_seconds_until_auto_pause = 900`

Storage contract:

- `infra/terraform/modules/storage/main.tf`
  - separate `product_images` and `private_artifacts` buckets
  - bucket versioning enabled on both
  - default SSE-S3 encryption on both
  - public access block enabled on both
  - bucket-owner-enforced ownership controls on both
  - lifecycle expiry on private-artifact upload and generated-artifact prefixes
- `infra/terraform/environments/dev/storage.tf`
  - wires the environment root to the shared storage module
- `infra/terraform/environments/dev/outputs.tf`
  - exports the product-image and private-artifacts bucket names and ARNs

## Live AWS Validation

Validation was run against account `046673074482` in `eu-central-1` using the
`tal` profile.

Identity check:

```bash
AWS_DEFAULT_PROFILE=tal aws sts get-caller-identity --output json
```

Observed account:

- `Account = 046673074482`

Aurora validation:

```bash
AWS_DEFAULT_PROFILE=tal aws rds describe-db-clusters \
  --region eu-central-1 \
  --query 'DBClusters[?DBClusterIdentifier==`ikea-agent-dev-db`].{id:DBClusterIdentifier,min:ServerlessV2ScalingConfiguration.MinCapacity,max:ServerlessV2ScalingConfiguration.MaxCapacity,autoPause:ServerlessV2ScalingConfiguration.SecondsUntilAutoPause,engine:Engine,engineVersion:EngineVersion}' \
  --output json
```

Observed cluster:

- `DBClusterIdentifier = ikea-agent-dev-db`
- `Engine = aurora-postgresql`
- `EngineVersion = 17.7`
- `MinCapacity = 0.0`
- `MaxCapacity = 2.0`
- `SecondsUntilAutoPause = 900`

Bucket validation:

```bash
AWS_DEFAULT_PROFILE=tal aws s3api head-bucket \
  --bucket ikea-agent-dev-046673074482-product-images \
  --region eu-central-1

AWS_DEFAULT_PROFILE=tal aws s3api head-bucket \
  --bucket ikea-agent-dev-046673074482-private-artifacts \
  --region eu-central-1
```

Observed buckets:

- `ikea-agent-dev-046673074482-product-images`
- `ikea-agent-dev-046673074482-private-artifacts`

Both resolved in `eu-central-1`.

## Conclusion

`tal_maria_ikea-v9b.4.4` is satisfied by the current repository plus the live
AWS state:

- Aurora already matches the intended pause-to-zero, low-cost scaling posture.
- The separate public product-image and private-artifacts buckets already
  exist under the expected names.
- Terraform already describes the database and storage resources that later
  deploy and storage tasks depend on.

The remaining infra follow-on work is not to choose or invent these resources.
It is to keep Terraform authoritative, keep outputs stable, and remove the
remaining workflow-side live discovery debt.
