# v3c: transactional aliases and absence-aware deployment

The previous deployer rejected a fresh board before writing because it hashed
newly declared libraries that did not exist. Its one-file transaction also could
not converge the route and Android aliases together. This change adds `--upgrade`
for a complete, same-platform package overlay and records absent native files.
No native library was rebuilt in this rollout.

## Frozen composition

Package: `/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate`.
Manifest SHA-256: `668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107`.
281 hashed members, 30 declared live hashes, 15 mounts. The generation directory
74d1d6d4 is a retained storage identity, not a hash of this new composition.
Source/recipe inputs are in the package's `handoff/inputs.json`, `artifacts.csv`
and B87 persistent archive. The static C++ recipe gap is resolved by oc-t4
commit `fb447ce1`; see `static-cxx-link-provenance.md`.

Selected native bytes: host d977bd15; ANL a9c9187d; provider 0509fe23;
CE/SQLite/VelocityTracker runtime 9e14bf20; liblog 8c81a937; bionic libc ee6034f5;
GLESv2 befb6ec7; stdc++ 7e06cd8b; OpenSLES 5891f899; TLS 39c2cfe9;
gapfill d1a1961d. ART 59e1bb45, bridge 84695d62 and native loader fde6f31c stay
unchanged. HTML is excluded. Installer is outside this package.

## Transaction and rollback

The deployer validates the old package SHA, owned mount stack, old live hashes,
platform prerequisites, and new alias/source consistency before writing.
It hashes existing files and records `before_absent` for declared native-library
paths under `/system/android/lib64`. Non-library paths must exist. Unexpected,
duplicate, incomplete snapshots and dangling links fail closed.

Staging is inside the rollback boundary. The old package and its single-file
layers remain underneath the new directory mounts. The parent starts only after
all 15 binds complete. A failure removes only owned new mounts, checks exact old
hashes and absence, restores the previous deployment ledger, restarts and verifies
the old runtime. An unexpected underlying file is **not deleted**: rollback
rejects that mismatch. For directory overlays, removing the overlay restores
absence automatically; individual `--add` placeholders retain their existing
owned-placeholder deletion checks.

`test_upgrade.py` exercises real deployment/rollback logic with a modeled mount
stack: 12 tests cover alias ordering, idempotence, a completed bind with a lost
marker, child-gate/transfer failure, foreign mounts, changed underlying files,
previous single-file layers, and fresh deployment/rollback with absent libraries.
The existing base/single-file/addition/bundle suites add 36 passing tests.
These tests do not constitute a real-board rollback drill.

## 5cd activation

5cd boot: `a42f2d6c-d29d-40aa-8145-51b4f85d0187`. The previous r17c overlay
2b201bda was verified and removed to expose package r8b d5000c4e. The new
transaction completed with five absent files recorded. `deployment-check/`
contains the actual HelloWorld screenshot, maps, SHA evidence and passing gate.
The child has one route ART and route openjdkjvm, with bridge 84695d62.

Then r17g `a35a782e0ad255e25b4dbb9f0d84baa3c95a9730bc8e80120163735e21ba10f2`
was overlaid as a separate Java variable. Master batch preflight confirms 16M
hilog, privacy off, 24h screen timeout and clock skew within 120 seconds.
`predictions.csv` records the expected affected walls before the five-app run.

The first controls invocation omitted the dedicated input root and failed before
launch with zero screenshots. It is retained in `runs/v3c-r17g-controls-5cd/`.
The corrected run uses `westlake-b90-controls-inputs`. Focus-row parsing reports
`foreground_unconfirmed`; actual screenshots and process counts remain separate.

## Replay and recovery

Use the revised worktree tool, not the older tool frozen in candidate/handoff:

```sh
scripts/lab/deploy_generation.sh SERIAL /Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate --upgrade --lane LANE
```

Use `--upgrade` only for an active owned same-platform generation. For a new
boot with no active ledger, omit it. Restore prerequisites through the accepted
reproducer first if the fresh board does not meet the platform gate. Take the
board lock and expose package r8b before either operation; a Java overlay is an
explicit separate transaction. Reapply the selected JAR only after verification.

For this 5cd session, `jar_overlay_5cd.py expose-new` verifies/removes r17g,
then `deploy_generation.sh SERIAL PACKAGE --rollback --lane cx-t0` restores the
previous package/layers; `jar_overlay_5cd.py restore` restores old r17c. This
helper pins this boot and receipt and must not be reused on another board.

## Verification limits

B9 lifecycle: five pass, one failed, one pendingreview. The failed old scenario
requires native manifest exports deliberately absent from retained 84695d62;
the user-selected v3a/v3c uses Java manifest fallback. No spec/test was weakened.
Historical B9 evidence does not certify v3c app behavior. New results and facts
are reported separately. 5ea and 61b are not deployed by this session.
