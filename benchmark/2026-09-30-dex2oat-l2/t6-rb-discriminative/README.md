# T6 read-barrier discriminative experiment (5cd, 2026-09-30)

**Verdict: CONFIRMED (functional).** The read-barrier-**ON** T5 boot image (kv `concurrent-copying=true`)
is unusable by the read-barrier-**OFF** board R155 runtime. Under a clean single-variable board test —
only the 27 boot-image files swapped, runtime fingerprint `0b81cdbe0ed9` unchanged — HelloWorld goes from
**lit** (its own UI) to **blank**, and appspawn-x's forked zygote/candidate children **SIGILL (signal 4)**.

## What was wrong before (why T4 passed but the image would still fail)

T4 proved the new libart's *layout* matches the board R155 (image v108/oat v230; all 244 `art_quick_*`
Thread/mirror offsets identical). But T4 never checked the **read-barrier compile-time master switch**.
cx-bms's T5 §2/3 found the smoking-gun kv difference: our T5 image was built with the r1 tree's default
`ART_USE_READ_BARRIER` (**on**, concurrent-copying=true), while the board R155 ART was built with it
**off** (concurrent-copying=false). Read barrier decides how every reference read is compiled and which GC
is used — libart/dex2oat/boot-image must all agree. A matching layout is necessary but not sufficient.

## The experiment (dispatch: board ACK(91) 2026-09-30T21:38)

Restore 5cd to U3, then overlay the existing (RB-on) T5 27-file boot image as a *discriminative* test:
predict the RB-off R155 runtime rejects it. Single variable — only `/system/android/framework/arm64/*`
changed via bind-mount; resident libart, JAR stack (J2/J3), installer all untouched.

| phase | boot.art | runtime fingerprint | HelloWorld | evidence |
|---|---|---|---|---|
| U3 baseline (RB-off v3c) | `2e4f8049` | `0b81cdbe0ed9` | **LIT** (own UI, ~88 KB shot) | `01-u3-baseline-HW-lit.jpeg` |
| overlay T5 (RB-**on**) | `f9524d82` | `0b81cdbe0ed9` (unchanged) | **BLANK** (38 KB shot, no app process) | `02-rbON-image-HW-blank.jpeg` |
| rollback → U3 (RB-off v3c) | `2e4f8049` | `0b81cdbe0ed9` | **LIT** again | `03-rollback-U3-HW-lit.jpeg` |

The board **never rebooted** (boot_id `0139c39f` throughout); appspawn-x cycled only via
`begetctl {stop,start}_service appspawn-x` — **never `kill -9`** (RUNBOOK L12).

## What actually happened under the RB-on image

appspawn-x's **parent** process starts fine, but the app-side is broken: its forked candidate/zygote
children hit **SIGILL (signal 4)** at 22:04:53–58 (`appspawn-restart-rbON-SIGILL.txt`), and a subsequent
`aa start` of HelloWorld leaves a **blank screen with no app process**. The RB-compiled quick code
(art_quick entrypoints / quick methods, generated for a read-barrier runtime) executes on the RB-off R155
libart and hits illegal instructions.

## The rule this sets

1. **The RB-on image is not cleanly rejected — it SIGILLs.** No explicit `ValidateOatFile` / read-barrier
   log, no new cppcrash faultlog. The board R155's image validation does **not** hard-reject on the
   `concurrent-copying` kv the way r1-tree `image_space.cc:3445-3451` (`IsConcurrentCopying != gUseReadBarrier
   → return false`, cx-bms) suggests it should; the mismatched code runs and crashes instead. Both paths
   prove incompatibility, but the observed one is more dangerous (executes bad code) — do not rely on a
   clean fallback.
2. **T4/T-layout gate must also compare compile-time switches** (read barrier / GC type / heap poisoning /
   debug), not just field offsets. Added to cx-bms's T5 §3 switch list and the t4 gate suggestion.
3. **Formal T6 acceptance must use the RB-off rebuild** (oc-t4 T3b/T5b: `ART_USE_READ_BARRIER=false`), whose
   generated image kv `concurrent-copying=false` matches the board.

## Board-op corrections captured this run

- **`hilog -x` returned a stale buffer** that missed the appspawn restart; you must `hilog -r` (clear)
  **before** the restart, then `hilog -x` after. The board shell also has **no `awk`** — parse `ps -ef`
  with `while read`/`grep -c`, never `awk` (the first scripted run's REJECTED verdict was a false positive
  caused by an `awk: not found` in the parent-up check; re-run manually to get the real signal).
- **appspawn-x recreates `/dev/unix/socket/AppSpawnX` on start** as `660:0:0:dev_unix_socket` — the
  `chown 0:6005 / chmod 0660 / chcon appspawn_socket` fix must run **after** start settles, and be
  re-verified (`stat -c '%a:%u:%g:%C'` == `660:0:6005:...:appspawn_socket:s0`); otherwise app clients
  cannot connect and apps stay blank even on the correct image.
