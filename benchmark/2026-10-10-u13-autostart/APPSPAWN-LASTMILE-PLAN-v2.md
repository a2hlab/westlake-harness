# Last-mile v2: appspawn-x won't start — root cause is the SERVICE_ATTR_INVALID latch + timing (not labels)

Supersedes the label theory in `APPSPAWN-LASTMILE-PLAN.md` (v1). Static only this round (61b handed to cx-t0; cx-t0 is
running the minimal "repaint system_file then start" experiment and restoring 61b to Mac-deploy state). This is v2
analysis + the implemented change; board A/B pending an approved window.

## Root cause (outer-pinned, confirmed from OH 6.1 init source)

`westlake-harness-bms-deploy/bms/src/upstream/openharmony-6.1.0.31/base/startup/init/services/init`:

- `init_common_service.c:674-692 IsServiceInvalid()` runs at **every ServiceStart**. If `SERVICE_ATTR_INVALID` is
  already set → logs `ServiceStart invalid:appspawn-x` and fails **with no clear path** (permanent for the boot). The
  attribute is set in only 3 places: **:685** (ServiceStart `stat(argv[0])` fails AND the path is **not** `/data/`-
  prefixed → `PATH_MAY_BE_NOT_EXISTS` tolerance; appspawn-x is `/system/...` so it latches), :910 (console-only),
  `init_service_manager.c:1400` (stop_all).
- **The exec-entry label IS load-bearing — but `appspawn_exec`, not `system_file`.** Under enforcing SELinux init
  `execv`s the appspawn entry point in the `appspawn` domain, which requires `/system/bin/appspawn-x` be labeled
  `u:object_r:appspawn_exec:s0` (stock `/system/bin/appspawn` is). 61b's fresh-boot Mac path failed with **init execv
  errno 13 (EACCES)** because the bound appspawn-x was `data_file`. cx-t0 relabeling the 56 sources to **`system_file`**
  didn't help (wrong label for the exec entry), and my v1/early-v2 `chcon appspawn_exec` was **silent (`2>/dev/null`)**
  so it never stuck. Fix: PR03 `pr03-runtime-recover.sh:158-161` order on the targets (appspawn-x → `appspawn_exec`,
  child/tgr/liblzma → `system_lib_file`), **`ls -Z` read-back, fail-closed** — implemented in recover.sh (non-silent).
- **Not a boot-time ENOENT:** cx-t0's fresh-boot read-only precheck shows `/system/bin/appspawn-x` + `child.z.so`
  **mount points exist at boot (0 bytes)** — so the initial `stat` succeeds. A 0B file exec'd by the ondemand path is
  **ENOEXEC → the child is reaped, NOT latched INVALID** (INVALID is a stat-fail path only).
- **Then exit 127 (the next wall):** with appspawn-x labeled `appspawn_exec`, `execv` succeeds but the process exits
  127 — the libs it maps (the whole `/system/android` tree incl lib64 **55/61** files, and
  `/system/lib64/libwestlake_thread_guard_registry.so`) are bound from `/data` and carry `data_local_tmp`, which the
  appspawn domain **cannot map**. So the *entire* runtime tree must be relabeled (`system_file`/`system_lib_file`), not
  just the exec entry. recover.sh now relabels the tree source-before-bind (non-silent) AND does a **whole-tree read-back
  count**: 0 `data_local_tmp`/`data_file` under `/system/android` + route-a + tgr, else FAIL (`MISLABEL_COUNT`).
- **Therefore** the last boot latched INVALID at some *moment* when `stat(/system/bin/appspawn-x)` failed — most likely
  during my v1 recover's mount activity (it ran late, at `bootevent.boot.completed`, i.e. after foundation/AMS were
  already connecting to AppSpawnX), or a `stop_all`. The exact moment can't be pinned: last boot's dmesg ring was
  already flushed.

## The fix (implemented) — be in place before AMS, keep stat continuous, and journal the moment

1. **Run recover at the `post-fs-data` bootstage** (Option A), not `bootevent.boot.completed`. `post-fs-data` is a
   confirmed OH stage (`trigger_processor.c:197`, `services/etc/init.cfg:162`) that runs after `/data` is mounted and
   **before** the boot-stage foundation/AMS that first triggers the ondemand appspawn-x. So the real U13 appspawn-x is
   bound before the first ServiceStart → that start `stat`s + execs real bytes → never latched. recover's old
   `bootevent.boot.completed` precondition is removed (it would now fail-closed); a short `/data` readiness wait is added.
2. **Never umount** (keep stat continuous — the outer's "保证 bind 期间 stat 不断"). recover only *binds* the real bytes
   over the existing 0B mount point; a bind is an atomic overlay, so `stat()` always resolves (no ENOENT window). This
   is a deliberate contrast with the donor PR03 recover, which `umount`s then rebinds (an ENOENT window that can itself
   trip :685). We do **not** adopt that.
3. **Journal dmesg + per-step timestamps to a persistent `/data` file** (`$ROOT/boot-journal-<boot_id>.log`). Since the
   dmesg ring is flushed by next session, recover now snapshots the appspawn/init/invalid dmesg lines at each step
   (START pre-replay, after replay+relabel, after finalize, READY). The acceptance aligns any `ServiceStart pathArgs
   invalid ... appspawn-x` line with the exact step.
4. **Relabel the exec entries per PR03 `:158-161`, read-back `ls -Z`, fail-closed (the errno-13 fix).** After the
   replay: `chcon u:object_r:appspawn_exec:s0 /system/bin/appspawn-x` + `system_lib_file` on child/tgr/liblzma, each
   **non-silent** (`2>>$LOG`) and **read-back verified** (`label_of` → `fail` on mismatch) so a relabel that doesn't
   stick surfaces loudly instead of as a white screen / EACCES. (The per-layer source-relabel-before-bind is kept as a
   belt so the bound target is never momentarily `data_file`.)
5. Carried from v1: idempotence (`exit 0` if already-READY this boot — fixes the 56×2=112 double-bind), `finalize_runtime`
   for the non-layer bits (boot.art/libc_musl symlinks, fonts, mali, anco params).

### Option B (physicalize the mount points to real U13 bytes) — documented, deferred

The outer's alternative: make `/system/bin/appspawn-x` + `child.z.so` the correct U13 bytes physically (same SHA →
no frozen-identity change; RUNBOOK confirms only a *different*-SHA swap trips `LOAD_ERROR:8`). This would make even the
physical (not just the bind) exec real bytes, covering an AMS connect that races before the bind. **Deferred**, because
at install time U13 is live and `/system/bin/appspawn-x` is **bind-mounted + the daemon may be running** → can't cleanly
rewrite the underlying physical (umount is busy). It would instead have to run inside recover while the path is unbound
at post-fs-data (writing `/system` every boot + a 0B-stub backup for rollback). Given Option A puts the real bytes in
place before AMS and the 0B stub already prevents an ENOENT latch, Option B is held as reinforcement **only if** the
window's journal shows a residual stat-fail. Not implemented (keeps rollback simple).

## Acceptance (pending window) — adds the dmesg/parent criteria

Beyond v1 (319/ready/listener + tap HelloWorld/ZigZag/Toutiao lit + 10-key regression + run_facts):
1. **`dmesg` shows NO `ServiceStart invalid:appspawn-x`** after the autonomous boot (and the persistent journal shows
   recover bound real appspawn-x bytes before the first AppSpawnX connect).
2. **appspawn-x parent is init** (PPID 1, UID 0) when it spawns on the first app tap.
3. A/B: `touch $ROOT/NO_FINALIZE` is the finalize A/B; the timing fix itself is validated by (1)+(2).

Rollback unchanged (`rollback-westlake-u13-autostart.sh`): restore backed-up init files + remove durable root + best-
effort removal of the finalize fonts/libc_musl additions; binds clear on reboot; no physicalize to undo. KA 40/40.

## Verification window request

Announce→LOCK→reboot(one)→read-only: journal + dmesg(no invalid) + 319/ready/listener + appspawn-x parent=init + tap 3
apps lit + 10-key run_facts→UNLOCK. On 61b after cx-t0 restores it, or the cx-bms-unified 5cd. ⚠ hub board may need a
USB re-plug. Report the window first; do not touch 61b until cx-t0 is done and the outer approves.
