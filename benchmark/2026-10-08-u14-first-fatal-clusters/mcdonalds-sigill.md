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
- **No faulting PC / no cppcrash — CORRECTED attribution (2026-10-09).** Earlier I blamed the empty `faultlogs/` on the
  `[ROUTE-A] child diagnostic fd unavailable: errno=13 Permission denied` line. **That is wrong.** The outer verified that
  EACCES line appears in **386/386 U14 hilogs — including lit keys like helloworld — and firefox/localsend wrote a cppcrash
  *despite* carrying that exact line.** So the diagnostic-fd EACCES is a universal, benign log artifact and is **NOT** why
  mcdonalds has no cppcrash. The real reason is the **sigchain termination path for SIGILL** (see "Why no cppcrash" below):
  the OH musl `signal_chain_handler` ends this SIGILL with `SIG_DFL` + **`rethrow`**, and that rethrow-to-default kills the
  process **without passing through OH's `DfxSignalHandler`** — so no cppcrash (hence no PC) is produced. SIGSEGV
  (firefox/localsend) instead reaches DFX and dumps. The missing PC is a consequence of the sigchain defect, not the fd.

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

## Why no cppcrash (deployed-artifact proof, not the fd) — see sigchain.md for the full chain analysis
The OH musl `signal_chain_handler` (in the deployed `ld-musl-aarch64.so.1`, the MUSL-SIGCHAIN logger) runs, for each signal:
**a loop over "special" sigchain actions → a single "usr sigaction" slot → `SIG_DFL` → `rethrow`** (proven by its own
format strings: `call %d rd sigchain action … sca_sigaction=%llx noreturn=%d`, then `call usr sigaction … sa_sigaction=%llx`,
then `SIG_DFL handler for signal: %d`, then `rethrow sig(%d) success`). For mcdonalds SIGILL(4): no special action claimed
it; the single usr slot held `7f095d6a6c` = **libart's handler, NOT akamai's**; libart did not recover → `SIG_DFL` →
**`rethrow`**. The rethrow re-raises against `SIG_DFL`, whose kernel default for SIGILL is *terminate*, and that default
termination path **does not route through OH's `DfxSignalHandler`** → no cppcrash. (SIGSEGV for firefox/localsend reaches
DFX and dumps — the difference is this SIGILL ended in rethrow→SIG_DFL.) The EACCES diagnostic fd is universal and irrelevant.

## Criterion / predicted move / minimal (read-only) — sigchain-centred
- **Criterion to confirm**: that akamai's SIGILL handler never occupies the OH musl usr slot (libart's does). Read-only,
  **no board needed** for the ordering — it is static in the deployed `ld-musl` strings/disasm (done, see sigchain.md).
  To confirm the *akamai-specific* PC: on a free board (read-only, do NOT run here) temporarily register a pre-usr trace in
  the sigchain or let DFX run for SIGILL (install DFX as a special action for signal 4) and read the faulting PC — expect
  libakamaibmp at an `MRS` of a trace/impl-def register. Secondary: `cat /proc/cpuinfo | grep -i Features` on 61b (only
  matters for the RNDR/crypto secondary candidate; the trace-reg MRS is EL0-illegal regardless).
- **Fix direction** (if confirmed): the route-A sigchain must (i) let an app-registered SIGILL handler actually reach the
  **usr** slot (today ART shadows it), and (ii) honor that handler's PC fixup and **not** force `SIG_DFL`+`rethrow` when the
  app handler "handled" the signal — i.e. match bionic/AOSP-libsigchain recovery semantics. Owner: signal-chaining compat
  (not ANW, not Flutter/sysconf). This is **runtime** behaviour → write the minimal critical experiment, do not change on a
  hunch (see sigchain.md ③).
- **Predicted move**: **0–1, uncertain → 搁置.** Even if the sigchain honors the probe's recovery, libakamaibmp is
  anti-tamper and may still refuse to run (environment-not-trusted) and stop at a verdict wall rather than light. The
  **class impact is the real payoff**: every app with a SIGILL/SIGSEGV-guarded native probe (anti-tamper/DRM/feature-detect)
  is exposed to the same defect — enumerated in `sigchain.md` ② (probe_scan.json).

## Summary
mcdonalds's SIGILL is most likely **libakamaibmp's anti-tamper system-register probe** (EL0-illegal `MRS` of trace/impl-def
regs) turned fatal by **OH route-A signal chaining rethrowing instead of honoring the app's SIGILL-handler recovery**,
with the empty faultlog caused by a **permission-denied diagnostic fd**. Not a Flutter/sysconf/ANW item. Confirmation
needs the faulting PC, which requires fixing the diagnostic-fd permission first (the one minimal on-board read-only step).
