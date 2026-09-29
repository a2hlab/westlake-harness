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

For this 5cd session, `jar_overlay_5cd.py expose` verifies/removes original r17c (the final selected overlay after rejecting r17h),
then `deploy_generation.sh SERIAL PACKAGE --rollback --lane cx-t0` restores the
previous package/layers; `jar_overlay_5cd.py restore` restores old r17c. This
helper pins this boot and receipt and must not be reused on another board.

## Verification limits

B9 lifecycle: five pass, one failed, one pendingreview. The failed old scenario
requires native manifest exports deliberately absent from retained 84695d62;
the user-selected v3a/v3c uses Java manifest fallback. No spec/test was weakened.
Historical B9 evidence does not certify v3c app behavior. New results and facts
are reported separately. 5ea and 61b are not deployed by this session.

## App findings and Java isolation

With r17g, NetGuard shows its main UI. Anki launches the wrong LeakCanary entry
under this board's older installer; its alive process is not Anki validation.
OONI returns to desktop with `libjnidispatch.so` failing to resolve `__errno`.
Auxio's VelocityTracker registration succeeds but its fragment construction
fails because BC loads `adapter.compat.WestlakeSecureRandomSpi` through the boot
class loader. Noice similarly fails to find
`adapter.security.OhTrustManagerFactorySpi`.

Following cc-t3's published request, r17h b8d74dd5 replaces r17g; the earlier
r17c overlay was briefly restored for a guarded transition, but no r17c app run
was made. `jar-ab-fingerprint-diff.json` proves that only the JAR changed across
all 115 fingerprinted files. Auxio now shows its five-tab music main UI and
logs successful SecureRandom. Noice still has the TrustManagerFactory CNFE.
Both are handed to cc-t3 with exact log paths. TLS39c and gapfilld1a load, but
TLS reports a failed native handshake self-test and a dormant socket factory;
this does not establish working HTTPS.

Screenshots and unedited master `facts.txt` are in `evidence/`. Focus parsing
remains unconfirmed, independent of screenshot review. The five-app predictions
were partly correct: NetGuard's ABI wall and Auxio's VT wall are removed; Java
provider loading and JNA's ABI lookup remain separate walls. This is a 5cd
native deployment result, not a claim that all apps or all three boards work.

Deployer frozen handoff: `/Users/zhaoyue/orca/workspaces/westlake-v3c-deployer-5fa85f77/`.
The candidate package bytes remain unchanged. Use this revision for other boards
only after their locks are assigned. No 5ea/61b write was performed here.

### r17h control regression

Final screenshot review found ZigZag white under r17h despite a live child;
HelloWorld remained normal. The previous r17g run of the same native package
showed ZigZag's menu. Therefore r17h is not accepted as a unified Java layer.
The failure was handed to cc-t3; the additional relayout change is a candidate
cause, not established here. The original r17c was restored and Auxio/HW/ZigZag
are checked again. Auxio again shows its five-tab music UI. Native package bytes did not change in this isolation.

### Final state and handoff

5cd remains on native package 668e4f7c plus its original r17c 2b201bda.
After restoration, HelloWorld, ZigZag menu and Auxio five-tab UI all appear in
actual t20 screenshots. Final SHA readback validates every declared live path,
with the external JAR explicitly substituted. The board lock is released after
verification. No other board was changed. Adopt this native package independently
of the pending unified Java choice; r17g and r17h are not regression-free here.

All screenshots referenced here are committed; raw full logs stay in the local
runs directories and selected failure lines are retained under evidence/. Raw
maps/process outputs preserve their original trailing whitespace.
