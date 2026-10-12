# Frozen restoration review

## Evidence and decision

The 221-file archive is a byte corpus, not a complete executable startup
closure. Treating it as the latter omits `runtime/appspawn-x`. This review does
not authorize deployment or infer visual success from fixture tests.

- t0 Git object: `257e829b3d5989fad43474fce3e858854cc0e326`;
  `toutiao_provider.py` SHA `203f19b38b46244ae96bab74ea4f31cb5da24cb681475ac4d268019287c942ce`.
- t4 freeze document SHA
  `b5904ec51f7f734204bbab8c998d4ab1407ad88908f4e91dceb6c2d9a702b640`:
  **12/12** listed objects independently matched and copied before testing.
  This is a content freeze, not a Git commit named `b5904`.
- Frozen t0 adapter: **8/8**, exit **0**, 2.601 seconds.
- Frozen t4 provider tests: **21/21**, exit **0**, 0.781 seconds.
- Independent storage-cleanup negative: exit **0** means the expected defect
  was reproduced; the actual derived rollback returns **2**. It had already
  emitted a successful control-rollback receipt before failing directory cleanup.

Decision: t4's corrected missing-only/unified-state routing passes the tested
offline cases. **257e is not deployment-ready**: startup closure, per-member
metadata and new rollback completion accounting must be resolved. No board,
VM, remote, app launch, signal, stop removal or candidate modification occurred.

## Actionable return points

### 1. Explicit additional runtime executable

`toutiao_provider.py:270` requires exactly 221 archive entries; the member loop
at line 282 only imports those entries. The new real source is
`benchmark/2026-10-12-v1-seal-execution/restore-spawner-source/source.json`:

- Target suffix: `appspawn-x` under the exact Route B runtime root.
- Actual byte SHA: `a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c`.
- Donor metadata: `755`, UID/GID `20011206`, `u:object_r:appdat:s0`.
- 5cd installed host UID/GID: `20011300`, not the donor's `20011206`.

Add an independently typed **extra runtime member** with source SHA, exact
target, target absence/preimage, explicit after metadata and rollback ownership.
Keep the archive count 221; separately account for the extra member. Include
it in the final plan, package manifest, projected seal, provider targets and
derived executor scope. A `stage_files` entry is not equivalent: the current
compiler only permits stage targets there. Never substitute U13's spawner.

### 2. Per-member metadata, not one blanket mode

At lines 291–294, `storage.runtime.file_after` is applied to every archive file.
The archive lacks per-file metadata; its SHA proofs do not prove permissions.
Provide a target-keyed metadata map for ELF executables, scripts, JARs and
libraries, with donor evidence and explicit target-UID derivation. `appspawn-x`
must retain executable permissions. `run.sh` is invoked through `/system/bin/sh`
and is rewritten by `real-start-parent-bounded.sh:9`; do not claim its execute
bit alone proves or blocks that path. Directory access and the actual writer's
authority also matter. Unknown metadata remains a binding blocker, not a guess.

### 3. Rollback receipt precedes new cleanup

`new_executor` inserts its storage cleanup after the original `rollback.json`
write. `review_restore_cleanup.py` runs the actual compiled transaction with a
recording device and fails the first `rmdir`: provider/executor return 2, yet
the receipt already says `ROLLED_BACK_CONTROLS_BOOT_TRIGGER_QUARANTINED`.

Emit final completion after cleanup, or explicitly separate control restoration
from storage-retained/cleanup-failed status and make retries unambiguous. Do
not delete legitimate runtime/JIT/app data to obtain an empty directory. This
finding concerns the new derivative, not a rejection of accepted b093 controls.

## t4 interface checks

The frozen providers use the standard four flags, independently pin their
program/common/executor, verify current boot and reuse the actual holder.
`u13_provider.py` now reads lowercase `state/layers/boot_id`, checks 56 unique
mounted targets, verifies owned baseline SHA and skips replay/installer.
The APK provider rejects unknown observations and existing version/hash drift;
the actual missing-only entry has no `cold_stop`, uninstall or replacement flag.
It performs an absence recheck, actual install and post-install readback.

The real data in `restore-5cd-preimages/results.json` supersedes earlier
unknown-preimage notes: stable boot `43bc3915-04bd-42ca-895e-26e8292911fa`,
runtime/stage absent, historical stop absent, 23 candidate/control targets
absent, HAP present with `df385638…`. The five existing ancestor metadata rows
are recorded in the accompanying advice. New-directory after metadata is a
proposed authority decision, not an observation of a directory that is absent.

Remaining integration bindings: additional runtime member support, per-member
after metadata, exact target startup closure, fresh outer authorization and an
explicit typed rollback entry. t4's old `appspawn-x: unknown` source note can now
be replaced in a **new** freeze using the real CAS source; do not mutate b5904.

## Scope and reproducibility

`restore-binding-advice.json` is non-executable advice, not a signed ticket or a
complete compiler input. Pending fields are null. It includes actual source
hashes, measured preimages and ancestors and clearly separates proposed schema
extensions. The original R2 52 files remain untouched. Raw runs and frozen
snapshots persist in `.artifacts/restore-257e-b5904/`; small raw test outputs are
also included in this review's independent landing list.

The child9544 probe status is a separate outer observation: 24 successful guard
evaluations did not reproduce the old5968 refusal. No further old SIG11/probe
analysis or crash repair is included here.
