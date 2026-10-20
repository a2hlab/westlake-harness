# T21 bounded read-only audit — BLOCKED (inputs inaccessible) (2026-10-20)

## Task

Independently verify child-11040 receipt facts against MAIN `benchmark/2026-10-20-t21-first-live-pair/results.json`: R20 lock/unlock0 counts, map/unmap/flush fields, first fatal source byte offset, NativeImage frame-available count. Read-only; no canonical/MAIN writes, no HDC, no builds, no permission changes. Conclusion ceiling: video not visually passed / ad-path CPU5 pairs only.

## Status: BLOCKED — no facts verified, no counts asserted

Both authoritative inputs are inaccessible from this lane, and no outer-supplied T21 input package exists (tasks #2/#3 inputs arrived under `.octos/*-inputs/`; nothing equivalent exists for T21). Per task instruction, no permission changes were made and sandbox repair was not retried.

## Exact commands attempted and failures

| Input | Command | Result |
|---|---|---|
| child-{8306,11040,13834}.stderr receipts | `ls $HOME/.local/share/westlake/toutiao-resume-20261020/t21-5cd-window-01/candidate-logs/` | `Operation not permitted` (sandbox denies home-dir reads) |
| MAIN comparison target | `ls benchmark/2026-10-20-t21-first-live-pair/` | `No such file or directory` in this tree; sibling MAIN direct reads already denied in tasks #1–#2 |
| Local git-object fallback | `git rev-parse HEAD` (task #1), `.git` inspection | worktree gitdir outside workspace; `~/.gitconfig` unreadable; git objects not readable in this lane |
| Workspace-wide search | `grep -rln 'first-live-pair\|child-11040\|t21-5cd' benchmark/ sources/ .octos/`; `find . -name '*t21*'` | 0 matches for the receipt/pair data; only pre-existing `benchmark/2026-10-20-t21-executor-independent-review/` (executor source review — no live-pair or child-11040 receipt content) |

## What would unblock

Outer supplies exact copies of the three candidate-log receipts and MAIN `benchmark/2026-10-20-t21-first-live-pair/results.json` under a `.octos/` input package (same pattern as tasks #2/#3), or grants read access to the stated paths. The five child-11040 facts then verify in one bounded pass.

## Ledger

0 device calls, 0 builds, 0 canonical/MAIN writes, 0 git commits, 0 permission changes. Deliverables: this README and `result.json` only.
