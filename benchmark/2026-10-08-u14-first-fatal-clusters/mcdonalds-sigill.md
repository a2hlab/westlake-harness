# mcdonalds early SIGILL (signal 4) — root-cause hypothesis: an anti-tamper SIGILL probe defeated by OH route-A signal chaining

U14 window1, 61b, `movers-mcdonalds-1`. Reclassified in disappeared.md from "process-disappeared" to **SIGILL (signal 4)**
(`APPSPAWN: com.mcdonalds.app pid 15264 exit with signal:4`). This pins the cause by static analysis (no board).

## ① Libs loaded before the SIGILL + why there is no backtrace
- At the SIGILL (12:31:39.955) only **system/route-a** libs had loaded (hilog dlopen/MUSL-LDSO): libart, libhwui,
  liboh_android_runtime, libjavacore, libnative_vsync, libframe_ui_intf, libaps_client, libmmi_knuckle,
  libsecurity_component_client_enhance, libwestlake_html_compat. **No APK native lib had finished loading.**
- The crash is **inside a `System.loadLibrary`** (hilog stack: `loadLibrary(System.java:1661)` → `Runtime.loadLibrary0`)
  — i.e. during the JNI_OnLoad / static-init of an APK native lib that was loading.
- The SIGILL handler that ran is `sa_sigaction=0x7f095d6a6c` = **libart.so** (route-a 74d1d6d4) — ART's crash handler, NOT
  an app feature-probe. The dozen per-tid "FREEZE_signo_4" MUSL-SIGCHAIN lines are the **crash-time thread freeze**.
- **No faulting PC is available**: `faultlogs/` is empty because the route-A child's diagnostic fd was denied —
  `12:31:31.523 [ROUTE-A] child diagnostic fd unavailable: errno=13 Permission denied`. So the cppcrash (with the PC) was
  never written. **This blinds us to the exact instruction — a finding in itself (route-A children can't dump native
  crashes).**

## ② Static scan of the APK's signature native libs (build-id, APK originals) — the probe instructions
| lib | MRS of privileged/ID regs (EL0-illegal) | crypto | LSE | RNG | sigaction imports |
|---|---|---|---|---|---|
| **libakamaibmp.so** (Akamai Bot Manager, anti-tamper) | **TRCSSCSR6, TRCSSCCR6** (trace regs), **S3_6_*/S3_7_*** (EL2/3 / impl-def), S3_0_C11_C2_7, S3_0_C13_* , CTR_EL0 | 8 | 69 | — | 4 |
| librealmc.so (Realm Core) | MIDR_EL1, CNTVCT_EL0, **RNDR / RNDRRS** (FEAT_RNG) | many | 5 | RNDR×2 | 3 |
**Reading `TRCSSCSR6`/`TRCSSCCR6` (trace) and `S3_6_*`/`S3_7_*` system registers from EL0 is ILLEGAL by the ARM arch (they
are EL1+/impl-defined) → `MRS` of them traps to SIGILL.** Akamai BMP reads them precisely to **probe the environment**
(detect tracers/emulators/hypervisors) — it installs signal handlers (4 sigaction imports) and reads these registers inside
a SIGILL-guarded probe: on success the reg value is used, on SIGILL the handler marks "not present / traced".

## Root-cause hypothesis (strong, evidence-aligned)
**libakamaibmp's SIGILL-guarded system-register probe runs in JNI_OnLoad at `System.loadLibrary` time. On stock Android/
bionic its own SIGILL handler recovers (advances PC past the faulting `MRS`, records the result). Under OH route-A the
signal chaining defeats that recovery:** MUSL-SIGCHAIN calls the chained handlers, reaches ART's handler
(`0x7f095d6a6c`), then `SIG_DFL` and **`rethrow sig(4)`** (seen in the log) → the "handled" probe SIGILL becomes fatal.
The permission-denied diagnostic fd then suppresses the cppcrash. Net: a benign-on-Android anti-tamper probe is turned
into a fatal SIGILL by the route-A sigchain semantics.
- Secondary candidate: librealmc's `RNDR/RNDRRS` (FEAT_RNG, ARMv8.5) or crypto — illegal if the board lacks the feature
  AND Realm's HWCAP gating is wrong under OH. Lower confidence (Realm normally HWCAP-gates these).

## ③ Board CPU features — needed (not in evidence)
No 61b `/proc/cpuinfo` Features string is in the existing evidence (faultlogs reference `/proc/cpuinfo` but don't quote it).
**However the akamai hypothesis does NOT depend on cpuinfo**: `MRS` of `TRCSSCSR6`/`S3_6_*`/`S3_7_*` from EL0 is illegal on
*every* AArch64 regardless of feature set. cpuinfo is only needed to judge the secondary (RNDR/crypto) candidate.

## Criterion / predicted move / minimal on-board (read-only) queries
- **Criterion to confirm**: capture the faulting PC. Currently impossible because the route-A child diagnostic fd is
  EACCES. So the MINIMAL on-board step (read-only, do NOT run here): (a) make the route-A child diagnostic fd writable
  (permission grant on the dump path) so the next SIGILL writes a cppcrash; then the PC confirms it is libakamaibmp at an
  `MRS` of a trace/impl-def register. (b) `cat /proc/cpuinfo | grep -i Features` on 61b (for the secondary candidate).
  (c) optionally `grep -rn "rethrow sig(4)" ` the sigchain source to confirm it ignores an app SIGILL handler's PC fixup.
- **Fix direction** (if confirmed): the route-A/bionic signal-chaining (MUSL-SIGCHAIN / our sigchain compat) must let an
  app-registered SIGILL handler's PC modification take effect and NOT rethrow to SIG_DFL when the app handler "handled" it
  — i.e. honor the probe's recovery, as bionic does. Owner: signal-chaining compat (not ANW, not the Flutter/sysconf items).
- **Predicted move**: **+1 past the SIGILL** if the sigchain honors the probe's recovery — BUT libakamaibmp is anti-tamper,
  so after recovering it may still refuse to run (environment-not-trusted) and the key would stop at an akamai verdict
  wall, not light. So **net lit move = 0–1 (uncertain)**; mark **搁置** pending the PC capture. Class impact: any app with a
  SIGILL-guarded native probe (anti-tamper/DRM/feature-detection) could be hit by the same sigchain defect.

## Summary
mcdonalds's SIGILL is most likely **libakamaibmp's anti-tamper system-register probe** (EL0-illegal `MRS` of trace/impl-def
regs) turned fatal by **OH route-A signal chaining rethrowing instead of honoring the app's SIGILL-handler recovery**,
with the empty faultlog caused by a **permission-denied diagnostic fd**. Not a Flutter/sysconf/ANW item. Confirmation
needs the faulting PC, which requires fixing the diagnostic-fd permission first (the one minimal on-board read-only step).
