# GCP Setup (Scaffold)

## Required Services
Enable and validate these before embedding implementation starts:
- Vertex AI / Gemini access in your target project
- IAM permissions for embedding requests

## Environment Variables
Set these in `.env` or shell:
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GEMINI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS`

## Local Auth Approach
- Use an application credentials file referenced by `GOOGLE_APPLICATION_CREDENTIALS`.
- Keep credentials outside the repo.

## Preflight Checklist
Run before development tasks:
1. `cp .env.example .env`
2. Fill required values
3. `make preflight`

This scaffold avoids calling live GCP APIs; it validates only local prerequisites.
