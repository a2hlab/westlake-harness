# One-reboot prerequisites and rollback boundary

## Evidence and minimum decision

BASE5 receipt is
`$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-execution/restore-v6-base-placement/execution/receipt.json`:
five afterimages verified, boot43bc unchanged, system RO, Enforcing; no reboot.
The v3 mode file requests permissive **for the next boot**, not an immediate
mode change. Receipt READY or a mode-file string is not actual Permissive.

Before ONE authorized reboot, require:

1. Exact new proof/prepared/admission/authorization pins and held holder; adapter
   process exit0, executor_rc0, transaction bound to the exact plan/serial/43bc
   boot, 487 backups and 487 unique exact target/SHA placed tickets, final
   placed.json state PLACED_ONLY/reboots0. No failed placement/UNKNOWN/124 or
   partial cleanup may be reported as completion. Actual deployment receipts
   have not been claimed by this reviewer.
2. Read back BASE5 five shapes, RO mount, unchanged boot, UID/GID20011300/HAP
   df385638…, new init CFG and actual startup/member pins from the freshly
   prepared plan. Historical stop remains absent; candidate/root or per-boot
   stop is not cleared. Preserve all raw command statuses and boot bookends.
3. Base v3 43491d3a trigger and RouteB CFG target must both be present, while
   old00cfg and Boat script remain absent. Exact CFG already contains DUMP plus
   CAPTURE_SCREEN in both permission lists; do not infer permissions from a
   different old CFG. No installer, manual spawner, runtime re-deploy or app
   launch is needed for this gate.

## Concrete read-only commands for outer

Set SERIAL to `5cd1e3dd00000000000000000923012c`; HDC is outer's explicitly
pinned local tool. These are commands to record, **not executed by BMS**:

```sh
"$LOCK_TOOL" held "$SERIAL"
"$HDC" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id; getenforce; cat /proc/mounts'
"$HDC" -t "$SERIAL" shell 'stat -c %a:%u:%g /data/app/el2/100/base/org.westlake.imehost/files; sha256sum /data/app/el1/bundle/public/org.westlake.imehost/entry.hap'
"$HDC" -t "$SERIAL" shell 'sha256sum /system/etc/init/00_westlake_u13_recover-v3.cfg /system/etc/westlake-u13-recover-v3.sh /data/westlake-demo/u13/selinux-mode /system/etc/init/01_westlake_u13_toutiao.cfg; ls -ldnZ /system/etc/init/00_westlake_u13_recover-v3.cfg /system/etc/westlake-u13-recover-v3.sh /data/westlake-demo/u13/selinux-mode /system/etc/init/01_westlake_u13_toutiao.cfg'
"$HDC" -t "$SERIAL" shell 'test ! -e /system/etc/init/00_westlake_u13_recover.cfg && test ! -L /system/etc/init/00_westlake_u13_recover.cfg && test ! -e /system/etc/westlake-u13-boat-overlay.sh && test ! -L /system/etc/westlake-u13-boat-overlay.sh && test ! -e /data/local/tmp/operator45/selfheal48/stop && test ! -L /data/local/tmp/operator45/selfheal48/stop'
```

Use the existing numbered transport's remote-rc marker; bare host rc0 is not
remote success. Persist each stdout/stderr/exit next to the new transaction.
Resolve all startup/member hashes from the actual newly admitted package, not
this report's historical T4 output paths. Require ROOT/stop and existing
ROOT/boots/*/stop absent without modifying them. The 487 per-file readbacks
already in executor raw evidence need not be duplicated as another full scan.

After the outer-only `hdc -t "$SERIAL" target boot`, require new boot bookends,
actual Permissive, newboot READY/56 base layers, correct init ancestry/socket,
no dmesg invalid, immutable RouteB startup/member identity and a fresh
ROOT/boots/NEW_BOOT attempt. Autonomous guardian intentionally waits for the
human foreground IMEhost icon; lack of child before tap is not failure. Do not
run aa/manual spawn or auto-consent. Screenshot feed/refresh/article judgments
remain separate from receipt/identity, with no seal assertion here.

## Precise rollback limit

The original transaction can perform guarded rollback before a legitimate
runtime mutation, using the original transaction directory and a new admission/
authorization binding **current** boot while retaining origin43bc/plan SHA:

```sh
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/r2-timeout/exact_realization.py" \
  --realization "$PROOF" --prepared "$PREVIEW" --execute \
  --admission "$ROLLBACK_ADMISSION" --admission-sha256 "$ROLLBACK_ADMISSION_SHA" \
  --authorization "$ROLLBACK_AUTH" --authorization-sha256 "$ROLLBACK_AUTH_SHA" \
  --lock-tool "$LOCK_TOOL" --lock-tool-sha256 "$LOCK_SHA" \
  --transaction-action rollback --out "$ORIGINAL_TRANSACTION"
```

No rollback auto-restarts an unsafe donor. It verifies backups and all current
objects before cooperative stop/CFG work; unknown inode/content, nonempty
storage or mounted additions preserve evidence and reject. No signals or
historical-stop deletion are authorized by this recipe. BASE5 is a separate
already-completed transaction: RouteB rollback does not revert its five paths.

**After normal launch, do not promise this old rollback will pass:**
real-start-parent.sh:12 rewrites the single runtime run.sh WID. Frozen executor
496fa's current-object scan then rejects that legitimate new SHA as
foreign/unobserved partial replacement, before writing stop or CFG. The
independent exact-function local case proves this in
`evidence/base-placement/t6-postboot-rollback-wid.json`; its only mocked command
is boot read. T6's WID-aware selfcheck does not alter this executor rollback
gate. If this case occurs, keep the transaction/actual WID evidence, stop
automatic recovery attempts and obtain a separately reviewed exact recovery
binding. Do not force old WID bytes back, erase stop, blanket-exclude run.sh or
claim successful rollback. This is a documented post-launch recovery limit,
not a new change to the frozen transaction.
