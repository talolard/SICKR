# Deployment Project Status

Read [guiding_principles.md](./guiding_principles.md) first.
Read [final_deployment_recommendation_2026-03-24_synthesized.md](./final_deployment_recommendation_2026-03-24_synthesized.md)
and [subspecs/00_context.md](./subspecs/00_context.md) for the current source
of truth. Those documents trump older deployment notes, review comments, and
superseded plans.

## Current Shape

The deployment project has a real AWS foundation in place:

- Route53, CloudFront, S3 buckets, EC2 host, and Aurora exist in account
  `046673074482`
- GitHub repo variables and Secrets Manager containers are mostly wired
- the product-image corpus is being pushed to S3 separately from app releases

The current implementation stack is still mid-transition.

## Important Simplification Adopted Today

The deploy model is now explicitly simpler than the earlier review stack:

- **environment bootstrap** is separate from **application deploy**
- normal app deploys run migrations plus seed verification
- normal app deploys do **not** require a host-local image catalog
- product-image URLs should point at same-host CloudFront URLs backed by the
  uploaded `masters/` keyspace
- `nginx` is no longer a required v1 architecture layer
- CloudFront should route directly to the `ui` origin by default and to the
  `backend` origin for `/ag-ui/*`

## What Is Implemented

- deploy specs and subspecs exist and are now updated to the simplified model
- the deploy bundle runner no longer assumes a host-local image catalog for
  steady-state deploy
- deploy env examples no longer advertise bootstrap-only host variables as part
  of the normal runtime contract
- the dead duplicate seeded-catalog readiness module has been removed
- the unused Postgres URL-shape helper and its dedicated test have been removed
- product-image URL helpers no longer carry dead run-id parameters now that the
  public URL contract is `masters/<image-asset-key>`
- Terraform now models direct UI/backend origin ports and no longer installs
  `nginx` in host bootstrap

## Major Remaining Gaps

- Terraform and CloudFront implementation still need to be fully aligned with
  the no-`nginx` routing model in the live environment, not just in code
- release/deploy automation still needs a clean separation between one-off
  environment bootstrap and steady-state image rollout
- final public-path validation on `designagent.talperry.com` is still pending

## Near-Term Priority

The next implementation priority should be:

1. finish aligning the deploy automation and Terraform with the simplified
   routing/bootstrap model
2. complete the product-image URL/seeding contract
3. validate the end-to-end public path and launch-readiness gates
