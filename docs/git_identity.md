# Git Identity Safeguards

## Required Local Identity
This repository should use public Git identity values:
- `user.name = Talo Lard`
- `user.email = talolard@users.noreply.github.com`

## Verification Commands
```bash
git config --local --get user.name
git config --local --get user.email
./scripts/check_git_identity.sh
```

## SSH Host Alias Reminder
Use the SSH host alias mapped to the public key/account in your `~/.ssh/config` when adding remotes.

## Pre-Push Check
Run `./scripts/check_git_identity.sh` before first push on a new machine.
