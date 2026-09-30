# Task 90 — offline replay and four-slot preparation

- Latest 19:44 dispatch: boards remain offline; implement replay + FakeBoard and four key lists only. No real hdc calls, locks or device writes occurred.
- Located exact N2 manifest, J2/J3 jars, FZ-001 and cx-t0 511d5797e mount/identity workflow locally. Reused transport and registry logic; no VM/network source lookup needed.
- N2 manifest's runtime JAR is a replaceable base d5000c4e. The other 38 live paths + one prerequisite + two installer artifacts are strict read-only checks in both shell and daemon root.
- Wrote idempotent two-layer replay, staging hashes, process/session guards and own-layer-only failure rollback. Missing native generation stops; this tool does not attempt native recovery.
- Four-board request has only three OH whitelist identities today; prepared 17/17/16/16 keys with D serial null. No question blocks offline preparation; fourth execution needs a registered/provisioned board.
- New tests 17/17 and old shard tests 19/19 passed. Contract lint 100%, 3 selectors passed. Source pins, one-line local audit and machine-readable results included.
- No new board evidence: screenshots/alive/replay outcome unknown. Final git add failed: worktree index.lock Operation not permitted. No new commit; base remains 8ff5a3f47 on analysis/bms-route-study. Outer must commit the new replay/shard/spec files and updated README/DIGEST/RUNBOOK/Rust selectors; prior staged task files were preserved. No push.
