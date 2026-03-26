# Aurora Pause-To-Zero Validation

Validated on: 2026-03-26

This note records the concrete validation for
`tal_maria_ikea-v9b.2.2`.

## Decision

The deployed database connection policy is:

- Aurora Serverless v2 writer endpoint
- no `RDS Proxy`
- deployed backend `DATABASE_POOL_MODE = nullpool`
- deploy/readiness polling must tolerate cold wake with retries for up to 180
  seconds

Local development may keep `queuepool` as the default.
The deployed ECS backend should not.

## Why This Is The Right Deployed Policy

The deploy target is intentionally low-duty-cycle and low-cost.
Keeping long-lived pooled connections open from the backend would work against
Aurora pause-to-zero.
`nullpool` keeps the deployed backend connection posture simple:

- requests open connections only when needed
- idle ECS tasks do not hold the Aurora writer awake
- deploy-time migration and readiness commands still use the same DSN and
  SQLAlchemy engine path

This aligns with `specs/deploy/guiding_principles.md`:

- low idle cost
- low operator burden
- explicit validation instead of guesswork

## What Was Validated

### 1. Terraform And The Live Cluster Allow Auto-Pause

Command:

```bash
aws rds describe-db-clusters --region eu-central-1
```

Relevant result for `ikea-agent-dev-db`:

- `Engine = aurora-postgresql`
- `EngineVersion = 17.7`
- `ServerlessV2ScalingConfiguration.MinCapacity = 0.0`
- `ServerlessV2ScalingConfiguration.MaxCapacity = 2.0`
- `ServerlessV2ScalingConfiguration.SecondsUntilAutoPause = 900`

Conclusion:

- the live cluster is actually configured for pause-to-zero
- this is not only a Terraform intention; it is present in AWS

### 2. The Live ECS Backend Uses `nullpool`

Command:

```bash
aws ecs describe-task-definition \
  --task-definition ikea-agent-dev-backend:10 \
  --region eu-central-1 \
  | jq '.taskDefinition.containerDefinitions[] | select(.name=="backend") | {environment, secrets}'
```

Relevant result:

- `DATABASE_POOL_MODE = nullpool`
- `DATABASE_URL` comes from the deployed Secrets Manager secret

Conclusion:

- the live backend is already running with the intended deployed pool policy
- the proof uses the real runtime posture, not a local approximation

### 3. Aurora Reached Zero Capacity While The ECS Backend Stayed Up

Command:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ServerlessDatabaseCapacity \
  --dimensions Name=DBClusterIdentifier,Value=ikea-agent-dev-db Name=Role,Value=WRITER \
  --start-time 2026-03-26T16:42:00Z \
  --end-time 2026-03-26T16:51:59Z \
  --period 60 \
  --statistics Average Minimum Maximum \
  --region eu-central-1
```

Observed datapoints before the wake probe:

- `17:42` through `17:50` CET: `Average = 0.0`, `Minimum = 0.0`, `Maximum = 0.0`

Companion command:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ACUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=ikea-agent-dev-db-1 \
  --start-time 2026-03-26T16:42:00Z \
  --end-time 2026-03-26T16:51:59Z \
  --period 60 \
  --statistics Average Minimum Maximum \
  --region eu-central-1
```

Observed datapoints before the wake probe:

- `17:42` through `17:50` CET: `Average = 0.0`, `Minimum = 0.0`, `Maximum = 0.0`

Conclusion:

- Aurora really reached zero capacity while the deployed backend service still
  existed on ECS
- the backend being up did not by itself keep the writer warm

### 4. A Real Backend Readiness Probe Woke Aurora And Succeeded

Command:

```bash
python - <<'PY'
import json, time, urllib.request

url = "http://ikea-agent-dev-alb-1739844720.eu-central-1.elb.amazonaws.com/api/health/ready"
started = time.monotonic()
with urllib.request.urlopen(url, timeout=60) as response:
    elapsed = time.monotonic() - started
    print(
        json.dumps(
            {
                "status_code": response.status,
                "elapsed_seconds": round(elapsed, 3),
                "body": json.loads(response.read().decode()),
            }
        )
    )
PY
```

Observed result:

- `status_code = 200`
- `elapsed_seconds = 15.444`
- readiness body reported:
  - database `ok`
  - schema `ok`
  - seed state `ok`
  - catalog data `ok`

Follow-up CloudWatch datapoint for the same minute:

- `17:51` CET `ServerlessDatabaseCapacity.Average = 1.8666666666666667`
- `17:51` CET `ACUUtilization.Average = 93.33333333333333`

Conclusion:

- the real readiness path wakes Aurora successfully from zero
- the first cold probe is materially slower than a warm probe
- a deploy/readiness poller must retry instead of treating the first slow DB
  connect as a hard failure

## Resulting Policy

The repo should treat the deployed DB policy as settled:

- deployed backend: `nullpool`
- deploy-time migration tasks: same Aurora writer DSN, same `nullpool`
- readiness polling: retry/backoff for up to 180 seconds
- no `RDS Proxy` unless a later measured failure proves `nullpool` is
  insufficient

This closes the open design question from the deploy review.
Later Terraform, workflow, and ECS tasks should consume this as established
input rather than re-deciding it.
