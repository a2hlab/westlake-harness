# T29 dual-artifact deployment data — pending

The T28 data assumed that only the shim changed. T29 changes the bridge and shim together: the first four artifacts remain byte-identical, while both new candidates have null SHA, size, artifact location and production receipt. Old bridge owner/GOT and shim export offsets are not reused as new evidence.

`executor.py` is byte-identical to T28/T21 (`693448c26cb72002031f58cca467691f09ac61674b2c76353eb71bd44a5b63bb`). This package adds no deployment transaction. The exact executable was exercised in 3 preview calls and 15 negative calls: both missing, either candidate missing, and either production closure missing, across preflight/apply/rollback. Every negative call rejected before Board import. Two Python tests additionally cover five data/source/admission mutations; one Rust test and the strict lifecycle passed. Raw argv/stdout/stderr/rc are indexed in `private-raw-index.json`; synthetic receipts exist only inside those offline fixture directories and are never production evidence.

Reproduce the pending check from the repository root:

```sh
python3 benchmark/2026-10-20-t29-deployment/check_final.py \
  --source-root "$PWD" \
  --out "$HOME/.local/share/westlake/t29-deployment-pending/new-check"
cargo test --manifest-path tools/spec-checks/Cargo.toml \
  --test toutiao_t29_deployment ttvideo_t29_deployment_pending -- --exact
```

The output directory must be new and persistent. The checker currently accepts only the pending template; it is not a production admission checker. Final production needs a separate data freeze and matching checker update, preserving this pending version. `handoff.json` records the precise integration boundaries.

Before that freeze, obtain both final ELF hashes/sizes and public source/build/raw/ABI receipts, regenerate bridge owner/GOT and consumer JNI/slot evidence, then bind the shim to that bridge and its three new export offsets. Player relocation offsets remain fixed. External static/live binding requirements in `bridge-binding-pending.json` and `three-slot-admission.json` are not enforced by the unchanged executor and must not be claimed as observed.

Preserved execution rules: exact 5cd/UID/cfg/runtime and current holder/boot/parent/host identity; physical/private hash, inode, metadata and label checks; all five backups plus compat-ABSENT marker before any swap; original apply-plan CAS and partial recovery; 1800-second window with 600 seconds reserved for recovery; fresh boot and original snapshot verification. The original executor still requires fresh host WID 29 for non-rollback execution. Historical `.t21-5cd-before-*` backup names remain unchanged and cannot be overwritten. No-parent recovery is rollback-only and proves physical recovery, not private-runtime recovery.

Root must collect a fresh T29 baseline and admission. A reused T26 before snapshot is not a fresh T29 sample. No device operation, build, approval, playback upgrade or seal claim is made here.
