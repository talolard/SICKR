# ECS Runtime Incident Playbook

Use this reference when a deploy "looks green" but the live runtime disagrees.

## Primary map

1. Pin exact identifiers.
2. Compare workflow output to live ECS service state.
3. Inspect the failed task and logs.
4. Reproduce inspection inside the real runtime image or task definition.
5. Compare migration metadata to physical schema objects.
6. Snapshot before mutation.
7. Repair the smallest trustworthy layer.
8. Re-run rollout and require the expected revision to become the only active serving deployment.
9. Smoke the public path.
10. Record the root cause and guardrails.

## Fast checklist

### Scope and operator environment

- Export `AWS_DEFAULT_PROFILE`, `AWS_REGION`, and `AWS_DEFAULT_REGION`.
- Record:
  - workflow run ID
  - release SHA
  - cluster ARN or name
  - service name
  - expected task definition ARN
  - load balancer or public base URL
- If the AWS CLI suddenly stops working, check profile resolution, region selection, and cached credentials before assuming an infra outage.

### ECS reality check

Run the equivalent of:

```bash
aws ecs describe-services \
  --cluster "$CLUSTER" \
  --services "$SERVICE"
```

Prove:

- what the service says its desired task definition is
- what the PRIMARY deployment is
- whether PRIMARY owns the full desired count
- whether old deployments still have running or pending tasks

Treat these as blockers:

- service desired count is zero when it should be serving
- PRIMARY task definition is not the expected revision
- PRIMARY desired count is lower than service desired count
- PRIMARY still has pending tasks
- old ACTIVE deployments still have tasks

### Failed task evidence

Inspect stopped tasks and their log streams for the intended revision. Find the first concrete runtime error, such as:

- missing database table
- bad environment variable
- import or startup error
- missing secret
- network or credentials failure

Do not patch blind from the ECS service event stream alone.

### Runtime inspection in the real container

Prefer a one-off task or command override on the same image or task definition that failed. Use it to inspect:

- database reachability
- current migration revision
- required tables or columns
- key config values after container startup

This step avoids false conclusions from local environments or stale assumptions about the deployed image.

### Database state triage

When migrations are involved, compare both:

- revision metadata, such as `alembic_version`
- physical schema state, such as `information_schema.tables` or table-specific column lists

Example queries:

```sql
select version_num from alembic_version;
```

```sql
select table_schema, table_name
from information_schema.tables
where table_schema in ('app', 'ops')
order by table_schema, table_name;
```

```sql
select column_name
from information_schema.columns
where table_schema = 'app' and table_name = 'threads'
order by ordinal_position;
```

If revision metadata says "head" but required tables are missing, assume the database was stamped or partially migrated incorrectly until proven otherwise.

### Safe repair order

1. Create a database snapshot.
2. Identify the last revision that is consistent with the physical schema.
3. Rewind or restamp only to that last proven revision.
4. Re-run migrations forward using the real deploy runtime.
5. Re-check both revision metadata and physical tables.
6. Only then re-run or continue the service rollout.

Avoid ad hoc table creation unless the migration chain is unrecoverable and a human has explicitly chosen that path.

### Rollout proof

Do not stop at "service stable." Prove:

- the service points at the expected task definition
- the PRIMARY deployment is that task definition
- PRIMARY owns the full desired count
- pending count is zero
- no older deployment still has running or pending tasks
- public endpoints respond successfully

If the built-in waiter semantics are too weak, add a stricter shared rollout checker in code and make workflows use it.

## Failure patterns from one real incident

### Pattern: green workflow, wrong backend still serving

Signal:
- workflow reports success
- ECS service desired task definition changed
- only the old revision is still running

Likely cause:
- rollout waiter accepts an incomplete state, often because PRIMARY exists but owns zero desired tasks

Fix:
- inspect `describe-services`
- define explicit readiness conditions
- codify them in a shared waiter used by every deploy workflow

### Pattern: migration task exits zero, startup still fails on missing table

Signal:
- migration task reports current revision equals head
- runtime crashes with `UndefinedTable` or similar

Likely cause:
- revision metadata advanced without the full physical schema being present

Fix:
- inspect physical tables directly
- rewind or restamp to the last proven-good revision
- replay migrations forward
- make migration entrypoints fail if required runtime tables are still missing after upgrade

### Pattern: health endpoint says healthy, startup path still breaks

Signal:
- readiness endpoint returns success
- startup or request path fails on missing runtime object

Likely cause:
- readiness only checks connectivity or revision metadata, not the actual runtime contract

Fix:
- expand readiness to verify the specific tables, columns, seed state, or other runtime invariants that the application truly requires

### Pattern: investigation produces contradictory signals

Signal:
- CI says success
- migration says success
- runtime says failure

Likely cause:
- different checks are proving different things

Fix:
- separate each contract explicitly:
  - migration metadata
  - physical schema
  - ECS rollout ownership
  - public request success
- resolve contradictions by trusting the most direct live evidence

### Pattern: AWS commands fail unexpectedly mid-incident

Signal:
- commands that worked earlier now fail
- profile resolution or auth errors appear unrelated to the deploy bug

Likely cause:
- expired SSO
- wrong profile
- wrong region
- corrupted local credential cache

Fix:
- pin profile and region explicitly
- inspect cache or auth state carefully
- back up any local credential file before changing it
- ask the human to re-authenticate when the repair requires an interactive login flow

### Pattern: local debugging drifts from the deployed image

Signal:
- local shell checks do not match live runtime behavior

Likely cause:
- local code, environment, or database assumptions differ from the deployed task

Fix:
- use a one-off task on the live image or task definition for inspection and targeted commands

## Evidence to preserve

- workflow run ID
- commit SHA
- expected and observed task definition ARNs
- ECS service JSON or a reduced snapshot of the important fields
- failing task ARN and log stream
- migration output
- schema inspection output
- snapshot identifier before live repair
- final public smoke result

## What to change in code after recovery

- tighten readiness checks to prove real runtime invariants
- tighten deploy waiters so workflow success matches serving reality
- return structured verification details in migration or inspection scripts
- document the exact rollout contract in repo docs

## Completion standard

Do not call the incident resolved until all of these are true:

- root cause is specific, not generic
- live state is repaired
- the expected revision is serving
- public smoke checks pass
- code guardrails were added where the prior contract was too weak
