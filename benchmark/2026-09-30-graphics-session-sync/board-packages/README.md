# Three boot-matched graphics replacement packages

Prepared from each board's current boot-matched active ledger; no device writes.
Read-only HDC boot IDs and SHA queries confirm runtime 9e14bf20, HWUI be59260f,
and TLS 39c2cfe9 on all three boards. All three ledgers currently reference
v3c manifest 668e4f7c, active_verified, with zero outstanding single replacements.
The per-board candidates consequently have identical manifest SHA 30f63ef7,
but separate paths and preparation receipts. Exactly one payload/live target
changes: runtime 9e14bf20 -> 32dfac83. Installer, host, ANL, TLS and Java bytes
in the packages are untouched.

**5ea first; 5cd and 61b only after 5ea success and explicit board release.**
5cd remains assigned to cc-t3. Do not run these commands while a sweep owns
the board. No locks were taken during this offline preparation.

Before native replacement the current JAR overlay must be recorded and retired
to package r8b d5000c4e. Restore the same recorded overlay afterwards and verify
its SHA. At preparation, 5ea/61b had r17p a0ed5c4f; 5cd had r17m a5cbd8d7
(and is scheduled to move to r17q). The observed JAR is evidence, not an
instruction to overwrite a later Java version. Use the board owner's latest
JAR receipt. The 5ea receipt is in westlake-harness-wiki,
benchmark/2026-09-29-wikipedia-line/deploy/r17p-after-hwui-rollback/receipt.json.

Commands below perform the requested one-file replacement, **not** an entire
package upgrade. The caller sets LANE to the actual held board-lock lane.
Immediately before use, check boot ID / active package SHA again. If either
changed, use prepare_for_base.py against the new active package instead of
using a stale preparation.

## 5ea

- Full key: `5ea34a4500000000000000001123012c`.
- Prepared boot: `51812b02-ec64-4d36-821c-ffd94531fb45`.
- Package: `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea`.
- Manifest SHA256: `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12`.
- Runtime SHA256: `32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7`.
- Rollback runtime SHA256: `9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f`.
- Ledger: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/5ea34a4500000000000000001123012c/51812b02-ec64-4d36-821c-ffd94531fb45-74d1d6d48210.json`.
- Dry-run: passed, device_io=false; see `5ea-dry-run.json`.

After sweep completion, lock/held confirmation, and Java overlay retirement:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5ea34a4500000000000000001123012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea \
  --replace /system/android/lib64/liboh_android_runtime.so --lane "$LANE"
```

Restore the same Java overlay, then HW/ZZ before Wikipedia onboarding,
fd-AppManager, fd-k9, fd-tusky, newpipe and noice. On any regression,
retire the overlay, undo the last replacement, and restore that same Java layer:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5ea34a4500000000000000001123012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5ea \
  --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane "$LANE"
```

## 5cd

- Full key: `5cd1e3dd00000000000000000923012c`.
- Prepared boot: `a42f2d6c-d29d-40aa-8145-51b4f85d0187`.
- Package: `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5cd`.
- Manifest SHA256: `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12`.
- Runtime SHA256: `32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7`.
- Rollback runtime SHA256: `9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f`.
- Ledger: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/5cd1e3dd00000000000000000923012c/a42f2d6c-d29d-40aa-8145-51b4f85d0187-74d1d6d48210.json`.
- Dry-run: passed, device_io=false; see `5cd-dry-run.json`.

After sweep completion, lock/held confirmation, and Java overlay retirement:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5cd1e3dd00000000000000000923012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5cd \
  --replace /system/android/lib64/liboh_android_runtime.so --lane "$LANE"
```

Restore the same Java overlay, then HW/ZZ before Wikipedia onboarding,
fd-AppManager, fd-k9, fd-tusky, newpipe and noice. On any regression,
retire the overlay, undo the last replacement, and restore that same Java layer:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  5cd1e3dd00000000000000000923012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-5cd \
  --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane "$LANE"
```

## 61b

- Full key: `61b0657200000000000000000324012c`.
- Prepared boot: `6fd44228-d33e-4f0e-9bf9-9a34842c72bf`.
- Package: `/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-61b`.
- Manifest SHA256: `30f63ef76b14a8ba2c1334940c66f5cc0e98aa4862152b81e6379f35d0b62c12`.
- Runtime SHA256: `32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7`.
- Rollback runtime SHA256: `9e14bf2005290c6e9e689fa779a1019bfcded7436c3a36d7a4973f462f46cd0f`.
- Ledger: `/Users/zhaoyue/orca/workspaces/westlake-generation-state/61b0657200000000000000000324012c/6fd44228-d33e-4f0e-9bf9-9a34842c72bf-74d1d6d48210.json`.
- Dry-run: passed, device_io=false; see `61b-dry-run.json`.

After sweep completion, lock/held confirmation, and Java overlay retirement:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  61b0657200000000000000000324012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-61b \
  --replace /system/android/lib64/liboh_android_runtime.so --lane "$LANE"
```

Restore the same Java overlay, then HW/ZZ before Wikipedia onboarding,
fd-AppManager, fd-k9, fd-tusky, newpipe and noice. On any regression,
retire the overlay, undo the last replacement, and restore that same Java layer:

```sh
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh \
  61b0657200000000000000000324012c \
  /Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83-61b \
  --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane "$LANE"
```

