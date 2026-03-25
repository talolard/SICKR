# Deployment Build, Publish, And Deploy Automation

## Summary

Implement the missing deploy side of epic `tal_maria_ikea-v9b.5` by turning the
existing release manifest into the artifact contract for both publication and
host deployment.

The implementation slice should:

- keep release publication authoritative only after both images and the manifest
  exist
- render one deploy bundle from the release manifest plus fixed host config
- send that bundle to the EC2 origin host over SSM
- run migrate, bootstrap, readiness, and UI checks from the host bundle
- preserve one previous deployed bundle so rollback can target the previous
  manifest without rebuilding images

## Scope

- `docker/compose.deploy.yml`
- `docker/env/host.env.example`
- `docs/deployment_runtime_contract.md`
- `scripts/deploy/*` for manifest loading, bundle rendering, host execution, and
  SSM payload generation
- `.github/workflows/release-publish.yml`
- one manual deploy or rollback workflow
- focused tests for the new deploy tooling

## Design

### 1. Keep the release manifest as the single deploy artifact record

The current repo already has release version resolution and manifest writing.
This slice should add manifest reading and validation so later scripts do not
reimplement JSON parsing ad hoc.

### 2. Render a host deploy bundle in CI

CI should turn the release manifest plus fixed deploy config into one bundle
containing:

- `release-manifest.json`
- `host.env`
- `backend.env`
- `ui.env`
- `docker-compose.yml`
- one host runner script

That bundle keeps the host deploy step small and deterministic. The host should
consume pinned image digests and env files, not repo source.

### 3. Use SSM to write and execute the bundle on the host

The deploy workflow should:

1. resolve the target instance by explicit repo variables
2. render the bundle locally in CI
3. send commands over `AWS-RunShellScript` that write the bundle onto the host
4. execute the host runner against that bundle
5. wait for SSM completion and fail closed on any non-success status

This avoids SSH as the normal operational path.

### 4. Make rollback target the previous deployed bundle

Successful deploys should update host-local deploy state so the previous release
bundle stays addressable.

Rollback should:

- redeploy the previous bundle by exact image digests
- skip schema migration by default because DB rollback is not assumed safe
- still rerun readiness and UI checks before success

## Human Gates

- `RELEASE_PLEASE_TOKEN` remains an optional Tal-owned gate when Tal wants a
  stronger GitHub token than the default workflow token.
- Deploy automation should fail with a clear message until Tal provides:
  - `AWS_DEPLOY_ROLE_ARN`
  - host-target repo variables
  - runtime secret ARN repo variables

Those are explicit deploy gates, not hidden assumptions.

## Acceptance Criteria

- Release publication still happens only after both images are pushed and the
  release manifest exists.
- The publish workflow can render a deploy bundle and trigger an SSM deploy.
- The host runner performs migrate, bootstrap, backend readiness, UI readiness,
  and one lightweight end-to-end check.
- Successful deploys retain enough state for a later rollback-to-previous flow.
- Manual rollback exists as a workflow entrypoint.
