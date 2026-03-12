# Vulture Notes

Source checked: official Vulture README via Context7 (`/jendrikseipp/vulture`).

## Official Guidance Relevant Here

- Vulture supports `pyproject.toml` config under `[tool.vulture]`.
- Command-line flags map to TOML keys by removing leading dashes and replacing remaining dashes with underscores.
- `sort_by_size = true` is the official way to surface the largest candidates first.
- Whitelists are Python modules that mark dynamically used names as live.
- `vulture mydir --make-whitelist > whitelist.py` is the official bootstrap flow for false positives.
- `min_confidence = 100` is the strictest setting; lower values trade more coverage for more false positives.

## Repo Implications

- FastAPI route functions, pytest fixtures, Alembic symbols, and Pydantic validators all need either decorator ignores or whitelist coverage.
- A small explicit whitelist is preferable to broad name ignores, except for `model_config`, which is a repeated Pydantic convention.
