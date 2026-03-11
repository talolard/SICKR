# Merge Runbook

This runbook is for explicit merge runs handled by `merger-agent`.

## Queue Contract

Merge queue parent: `tal_maria_ikea-0uk`.

Each queued item must be:

- `type=merge-request` (or `label=merge-request` on bd versions that cannot mutate type)
- `status=blocked`
- `assignee=merger-agent`

Because items are blocked, they do not appear in normal `bd ready` pickup.

## Start a Merge Run

```bash
make merge-list
```

This lists blocked merge-request items owned by `merger-agent` that are green on required checks.

Other views:

```bash
make merge-list-all
make merge-list-failing
```

Use `make merge-list-failing` to review non-green PRs and copy suggested `bd update ... --assignee <agent>` commands.

## Process Loop (Per Item)

1. Set item to in progress.
2. Read branch/PR/base from bead description.
3. Attempt merge against latest target base.
4. Resolve conflicts:
   - trivial formatting/pattern conflicts: fix directly
   - logic conflicts: infer intent from PR/task context, then implement and validate
5. Run validation (`make tidy` minimum once after fixes).
6. On success:
   - merge PR
   - close merge-request bead
7. On failure:
   - append concise failure notes to bead
   - set bead back to blocked
   - continue to next item

## Normalize Queue Shape

When queue drift occurs (wrong type/status/assignee), run:

```bash
make merge-normalize
```
