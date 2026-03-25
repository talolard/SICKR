# Docker Notes

This directory defines the container build inputs for the deploy system.

## Platform policy

- Local image builds on Tal's macOS machine should default to `linux/arm64`.
- Production deploys target ECS Fargate with `X86_64`, so published release images must be built in CI for `linux/amd64`.
- Do not use local macOS builds as the source of truth for deployable images.
- If a local container build is needed for debugging, treat it as a developer convenience only and do not push it as the release artifact.

## Operational implication

- Use GitHub Actions for release image builds and pushes.
- Keep local Docker usage focused on inspection, debugging, and small validation steps.
