# ACK #91 — SOURCE-CLOSEOUT

Delivered production-version Boat source, portable offline recipes, fixed input/toolchain locks and new
actual execution logs. C7=1bea0f and C4=f6b806 replay exactly, rc0. Signal compiles/links/strips rc0; exact
comparison rc2 (0987e589 versus7a931), 19 differing bytes only in GNU build-id. No note replacement,
no old SHA change, no historical-log claim, no new API, no device call and no bridge8ab change.

9 Python +1 Rust PASS; source user-path checks PASS. Agent-spec quality/boundary PASS; two human scenarios
SKIP, lifecycle rc1 honestly retained. Outer acceptance remains required.

Local complete input/toolchain/raw-log/output archive:
`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-verified-source-closeout/boat/.artifacts/boat-production-closeout.tar.gz`

SHA256: `29e883638f23c9d13ca49b95535d02e29f3956970efe9f8ed0a283eea735e403`, 437507873 bytes.
SSH persistence attempt was refused by the sandbox (rc255, Operation not permitted). Outer can execute:

```sh
PERSIST_OUT="$NEW_PERSISTENCE_RECEIPTS" bash "$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-verified-source-closeout/boat/persist-outer.sh"
```

This ACK is saved in the allowed worktree for the outer to append to canonical blackboard #91;
this lane does not write MAIN or bypass its filesystem sandbox.
