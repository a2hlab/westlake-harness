# Last-mile: make the autostart light apps (appspawn-x) — static analysis + fix (pending board window)

> **SUPERSEDED by `APPSPAWN-LASTMILE-PLAN-v2.md`.** This v1 pinned the SELinux `data_file` label as the cause; cx-t0
> showed relabeling the 56 sources did NOT fix it. The real cause is the init `SERVICE_ATTR_INVALID` latch + recover
> timing (ran too late, after AMS). Kept for history; read v2 for the current design.

Outer ACK(91): solve the last mile **in the autostart** (sealed board power-cycles to a lit demo). Static only this
round (61b handed to cx-t0; not touched). This is the analysis + the implemented fix; board A/B test pending a window.

## ① What the validated reboot-PASS recipe does (00.Workspace)

`~/orca/00.Workspace-games-ad1ab0a7/var/state/pr03-reboot-test/` is the reboot-proven recipe (`result/
HelloWorld-after-reboot.jpeg` + `HelloWorld-second-reboot.jpeg` = HelloWorld lit after reboot, twice). It ships three
files: `00_pr03_runtime_recovery.cfg` (the mount-worker service, `start-mode: boot`, caps DAC_OVERRIDE/CHOWN/FOWNER/
SYS_ADMIN, secon `u:r:su:s0`), `pr03-runtime-recover.sh` (the worker), and **`appspawn_x.cfg`**. Read line-by-line:
- The appspawn-x **service is `ondemand: true`** (init `listen()`s `/dev/unix/socket/AppSpawnX` and lazily spawns the
  daemon on the first AMS connect; `critical`/`start-mode` absent). The worker **does not start appspawn-x** — it relies
  on ondemand + "first APK tap is the trigger".
- The worker, AFTER binding the layers, does a **post-mount setup**: `chcon` every bound file to its canonical context
  (`system_file` / `system_lib_file` / `appspawn_exec` / `system_etc_file`), `ln -sf arm64/boot.art …/boot.art`,
  `chcon` the boot image, `chcon`+copy `fonts.xml` to `/system/etc/fonts.xml`, `ln -sf …/ld-musl-aarch64.so.1
  /system/lib/libc_musl.so`, `chmod 0666 /dev/mali0`+relabel, and sets `persist.sys.abilityms.support_anco_app=true` /
  `prefork.enable=false` / abilist.

## ② Compare: init's boot-parsed service def vs the U13 layer — IDENTICAL (so the service def is NOT the difference)

- 61b's physical `/system/etc/init/appspawn_x.cfg` = **3165 bytes = byte-identical** to the repo/U13 `appspawn_x.cfg`
  (`bms/src/adapter/framework/appspawn-x/config/appspawn_x.cfg`) **and** to the reboot-PASS `pr03-reboot-test/
  appspawn_x.cfg` (`diff` = identical). All three are the proven **ondemand** definition.
- So init on 61b parsed the correct ondemand def at boot. On the 61b run, hilog showed AMS **did** connect
  (`routing to appspawn-x for Android app` + `Create socket success /dev/unix/socket/AppSpawnX`) but the daemon never
  materialised (`pidof appspawn-x` empty). I.e. the ondemand spawn is attempted but the daemon **can't load/serve**.
- `deploy_generation.py` `start()` works at deploy time because it `stop_service`→`start_service appspawn-x`, waits for
  the pid, then **fixes the socket** (`chown 0:6005 && chmod 0660 && chcon u:object_r:appspawn_socket:s0
  /dev/unix/socket/AppSpawnX`) — but that runs over a runtime where the **post-mount setup is already in place**.

**Conclusion:** the difference is **not** the service definition (identical/ondemand/proven) — it is the **post-mount
setup my recover worker omitted**, and the outer (ACK(91)) pinned the precise mechanism:

> On 61b the bound files (`/system/bin/appspawn-x` etc.) carry label **`u:object_r:data_file:s0`** — a bind mount
> shows the SOURCE inode's label, and the `/data` archive is `data_file`. init execs appspawn-x under secon
> `u:r:appspawn:s0`; **SELinux denies exec of a `data_file` entry point** → ondemand connects the socket but the daemon
> never spawns, and `begetctl start_service` returns 0 without starting. The Mac deploy works because
> `deploy_generation.py:511` does `chcon -R system_file` on the `/data` payload SOURCE (as hdc root) before the runtime
> is used.

My recover's relabels were **silently failing** (`chcon … 2>/dev/null`) in the boot service, so the bound files stayed
`data_file`. My recover service already has the secon/caps to relabel (`u:r:su:s0` + DAC_OVERRIDE/CHOWN/FOWNER/SYS_ADMIN,
same as PR03's `pr03-runtime-recover.sh:158-161` which relabels to `appspawn_exec`/`system_lib_file`). The bug was
(a) not relabeling in the deployed version at all / (b) doing it silently after bind. The plan's "narrowly justified
changes if execution would otherwise fail" clause applies.

## ③ The fix (implemented in `payload/scripts/westlake-u13-recover.sh` → `finalize_runtime()`)

Two parts, keeping appspawn-x **ondemand, started by init** (never su-exec'd → no `PR_SET_KEEPCAPS` wall):

**Part 1 — relabel the SOURCE before bind, verified, fail-closed (the actual fix; in the replay loop).** For every
layer, `chcon` the `/data` archive source to its canonical context (`ctx_for`: appspawn-x → `appspawn_exec`; `.so`/
lib64/route-a → `system_lib_file`; `.jar` → `system_file`; `.json` → `system_etc_file`; `/data/app/*` →
`data_app_el1_file`; android tree → `system_file`, with lib64 + boot image refined to `system_lib_file`) **before**
`mount -o bind`. chcon stderr now goes to the recover log (no more `2>/dev/null`). After binding
`/system/bin/appspawn-x`, **verify** its label == `appspawn_exec` and **FAIL** closed if not (so a relabel denial
surfaces loudly with the secon/caps hint, instead of a silent white screen).

**Part 2 — `finalize_runtime()` for the non-layer runtime bits** (after replay): `ln -sf arm64/boot.art
/system/android/framework/boot.art` + relabel the boot image (inside the bound tree, no `/` rw); `chcon`
`/system/android/etc/fonts.xml`; copy fonts.xml → `/system/etc/fonts.xml` and `ln -sf …/ld-musl-aarch64.so.1
/system/lib/libc_musl.so` (these two are **outside** the bound trees → a `/` **rw remount** just for them, re-sealed
`ro`, SYS_ADMIN cap, no setenforce); `param set` anco/prefork/abilist (persist; usually already set) + `chmod 0666
/dev/mali0`+relabel. Gated by `$ROOT/NO_FINALIZE` for A/B.

Idempotent/best-effort. KA 36/36 (finalize presence/steps/gate/reseal/no-setenforce + source-relabel checks).

**Why not override the appspawn_x.cfg service (the initial hypothesis):** unnecessary — the service def is identical and
proven; overriding a core OH file is higher-risk. Kept as a **fallback (Fix B)** only if finalize alone does not render:
physically replace `appspawn_x.cfg` with a non-ondemand variant started by init on `sys.westlake.demo.u13.ready=true`
(init parent, after recovery). Not implemented; would need its own backup/rollback.

## Answers to the outer's checks

- **① chcon real return / recover secon+caps allow relabel:** the deployed recover did the relabel *silently*
  (`2>/dev/null`) or not at all, so a denial was invisible. Now chcon stderr goes to the recover log and the critical
  appspawn-x relabel is **verified + fail-closed** — any `relabelto appspawn_exec` denial will show in the log and stop
  the run loudly. The recover service's secon is `u:r:su:s0` with caps DAC_OVERRIDE/CHOWN/FOWNER/SYS_ADMIN — the **same**
  as PR03's `pr03-runtime-recover.sh` (which relabels to `appspawn_exec`/`system_lib_file` at lines 158-161), so the
  domain is permitted to relabel; the window will confirm the label actually sticks on 61b.
- **③ idempotence / the 112 layers on 61b:** fixed last commit — the "already READY this boot" branch now `exit 0`s
  instead of falling through, so a re-trigger no longer re-replays (which is what left 61b at 56×2=112 binds during my
  diagnosis). 61b's current 112 is from that; cx-t0's ticket restore + a clean reboot resets to a single 56.

## Rollback

- A/B: `touch $ROOT/NO_FINALIZE` → next boot skips finalize (old behaviour) without uninstalling.
- Full rollback (`rollback-westlake-u13-autostart.sh`) restores the backed-up init files + removes the durable root; the
  bound overlays clear on reboot. The two physical additions finalize makes outside the bound trees
  (`/system/etc/fonts.xml`, `/system/lib/libc_musl.so` symlink) are documented for the rollback to remove; the anco
  params are `persist.*` already set by any U13 deploy (cx-t0's included), so leaving them is a no-op.

## On-board verification (pending an approved window — 61b after cx-t0, or the unified 5cd)

1. A/B baseline: `touch $ROOT/NO_FINALIZE` → reboot → confirm apps still white (reproduces the gap).
2. Fix on: remove the marker → reboot → **tap HelloWorld/ZigZag/Toutiao → screenshots lit** (the acceptance). Watch
   `pidof appspawn-x` after the tap (should spawn + stay, UID0/PPID init), and hilog for any appspawn-x load error if
   still white (would point at the minimal load-bearing subset of finalize).
3. Re-confirm 319/ready/listener unchanged; one reboot per the outer's cadence.

Announce→LOCK→(set NO_FINALIZE A/B)→reboot→verify→remove marker→reboot→verify lit→UNLOCK→facts→PROGRESS(91). ⚠ board on
hub may need a USB re-plug. Report the window request first; do not touch 61b until cx-t0 has restored it and the outer
approves the window.
