# Vulture

Use `uvx vulture` from the repo root. The repo config narrows the scan to active Python sources and tests, ignores known framework decorators, and loads `vulture_whitelist.py`.

## Why The Config Exists

- The raw exploratory command `uvx vulture src .` is useful for seeing the full noise profile.
- It is not a stable signal for this repo because it drags in `legacy/`, Alembic revisions, and decorator-driven framework entrypoints.
- The configured run keeps the signal focused on active runtime code and small compatibility shims we intentionally retain.

## Whitelist Policy

- Add entries only for framework-driven or compatibility-driven false positives.
- Prefer explicit symbol references over broad `ignore_names`.
- Delete genuinely unused helpers instead of whitelisting them.
