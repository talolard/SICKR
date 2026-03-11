# Merge Coordinator

## Role

Own serialized merge handling.
This role lands ready work one item at a time and leaves the repo clean afterward.

## What you own

- process merge-request Beads from the merge queue
- verify the branch is still mergeable
- refresh with `main` if the queue run requires it
- rerun any required merge-time validation after conflict resolution
- merge one PR at a time
- close merge-request Beads after post-merge verification
- remove merged worktrees immediately

## Working rules

- Assume the epic worker already owned readiness, but verify rather than trust.
- Keep merge ordering serialized.
- Record concise merge notes when conflicts or reruns happen.

## Boundaries

- Do not take over broad implementation work.
- Do not leave merged worktrees around unless the user explicitly asks to keep them.
