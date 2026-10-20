# T31 implementation peer: WID29 only

The design snapshot preceded the outer decision to restrict both apply and recovery to WID29. This review supersedes that scope discussion while preserving the original report.

Independent rerun: 7 author tests passed. The 64 combinations execute real successor source blocks and inspect emitted guards; they do not run a complete transaction. Local guarded shell tests additionally reject changed backup/compat bytes, changed metadata/label, missing files and missing or corrupted ABSENT markers. OH stat and SELinux output are substituted on the host. The original stdout's “No shell/device execution” is stale: the correct limitation is local guarded shell only, no HDC/device/full transaction.

Five additional actual admission-parser negatives reject private SHA, private device/inode metadata, private label, boot and namespace drift.

The independent scope-chain check runs the actual scope_apply CLI, then the unchanged 693448 executor's verbatim plan-generation/write block, then actual validate_origin. Scope fields are not manually inserted into the generated admission, and the plan is never patched. The old unscoped admission and a later changed scoped admission are rejected. This uses synthetic fresh identity data and does not execute the full executor CLI. Production must pass that scoped admission into apply before the original executor writes its plan.

No current source blocker in this bounded offline scope. Actual recovery, retained deployment and playback remain unknown here. `implementation-results.json` pins the exact sources; `implementation-private-index.json` indexes persistent raw snapshots and outputs. The two `.actual.py` files preserve the independent fixtures verbatim; their replay context is the corresponding private scope-chain-01/implementation-02 directory, with T31_MAIN pointing to the repository.
