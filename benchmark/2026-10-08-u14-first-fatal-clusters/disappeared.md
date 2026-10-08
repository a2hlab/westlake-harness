# Cluster-3 "process-disappeared, cause unknown": toutiao + mcdonalds re-investigated (U14 window1, board 61b, offline)

Both ran in U14 window1-r3 on 61b (`movers-<key>-1`). Both `faultlogs/` are **empty** (no cppcrash). Evidence below is
per-line from the run's own files; where the cause is not in the captured files it is written **unknown**, not inferred.

## mcdonalds (pid 15264) — RECLASSIFY: it is a **SIGILL (signal 4)**, not "disappeared/unknown"
Liveness: `processes-t5` has 15264; `processes-t20` does not → died in the t5→t20 window.
**① System side — NOT lmkd/memmgr; it self-crashed with signal 4:**
```
12:31:39.955 15264 15285 W MUSL-SIGCHAIN: signal_chain_handler call usr sigaction for signal: 4 sig_action.sa_sigaction=7f095d6a6c
12:31:39.955 15264 15285 W MUSL-SIGCHAIN: signal_chain_handler SIG_DFL handler for signal: 4
12:31:39.955 15264 15285 W MUSL-SIGCHAIN: pid(15264) rethrow sig(4) success.
12:31:40.019   919 1991 I AppMS: [AMSI3279]kill reason=OnRemoteDied, 15264   <- AMS REACTS to the already-dead process
12:31:40.021 24941      W APPSPAWN: com.mcdonalds.app with pid 15264 exit with signal:4
```
`signal:4` = SIGILL. The app's own signal-4 handler (`sa_sigaction=7f095d6a6c`) ran, then SIG_DFL → rethrow → died. The
AMS `kill reason=OnRemoteDied` is AMS cleaning up AFTER the death, not the cause. `lmkd` lines in this run = **0**.
**② Last child action before the SIGILL:**
```
12:31:39.099 [COROUTINE-FIX] CoroutineStart class=kotlinx.coroutines.CoroutineStart (Kotlin coroutines init)
12:31:39.944 java.lang.ClassNotFoundException: Didn't find class "adapter.activity.ManifestOrientat…" at ClassLoader.loadClass(312)
12:31:39.955 SIGILL (signal 4)
```
Thread 15285; the SIGILL lands during early app init (coroutine start / class loading), right after a
`ClassNotFoundException` for a route-A `adapter.activity.Manifest…` class (likely a caught probe).
**Cause of the illegal instruction: UNRESOLVED** — the signal-4 handler at `0x7f095d6a6c` is not in `maps-t5-15264.txt`,
and there is no `abort`/`__cxa`/`terminate`/trap line. SIGILL typically = a call through a bad/garbage function pointer
landing on non-code, or an unsupported instruction.
**④ Realm/sysconf: NOT present.** The only `sysconf` line is `OH_RegHook: libcore.io.Linux::sysconf -> libjavacore.so`
(a routine JNI-hook install), NOT a Realm/SlabAlloc native crash. There is **no** `realm`/`SlabAlloc`/`librealmc` crash
trace. → **Do NOT fold mcdonalds into the sysconf cluster**; it is a distinct SIGILL whose cause is unresolved from this run.
**③ vs prior (U10.1-T8, the latest pre-U14 obs; no distinct U13 run — no_change):** prior first-fatal was a Java
`NullPointerException`; U14 is SIGILL → **different mechanism (flipped)**.
**Predicted move:** 0 in any current in-flight fix (SIGILL cause unresolved, not sysconf, unowned) → **搁置**; to pin it,
re-run with the signal-4 handler's lib resolved (maps at crash time) or a backtrace (the app's own handler suppressed the
OH cppcrash — disable it or capture the pre-rethrow frames).

## toutiao (pid 22296) — cause genuinely UNKNOWN: hilog capture ended BEFORE the death
Liveness: `processes-t5` has 22296; `processes-t20` does not → died in t5→t20.
**① + ② But the captured hilog ends at `12:35:44.806`, and toutiao's last line is `12:35:44.465` showing NORMAL startup:**
```
12:35:43.9 22296 OH_Parcel [stub] markForBinder/writeInterfaceToken; [ONLINE-CM] getActiveNetworkInfo -> connected WIFI
12:35:44.465 22296 [G2.5-PIB] ApplicationInfo com.ss.android.article.news icon/iconRes/labelRes/theme …
12:35:44.806   919 (hilog ends — IPCObjectStub line, not toutiao)
```
No SIGILL/SIGSEGV/SIGCHLD-exit, no `lmkd`/`memmgr` kill, no AMS kill, no ANR/watchdog, no `avc: denied`/sandbox denial for
22296 in the captured window — because the **hilog capture ended (~12:35:44.8) before the t5→t20 death**. `lmkd` lines = 0.
**④** n/a (not Realm).
**③ vs prior (U10.1-T8):** prior was `no-observed-termination` (alive, no terminal); U14 it did die (gone by t20) but the
exit is outside the captured hilog → **inconclusive whether same mechanism**.
**Cause: UNKNOWN** (not in the captured files; not inferred). **Predicted move: 0** → **搁置**; needs a re-run whose hilog
capture extends past the process exit (the current capture window closed too early for toutiao).

## Summary
| key | U14 first-fatal (this analysis) | system-side cause | in sysconf cluster? | predicted move |
|---|---|---|---|---|
| mcdonalds | **SIGILL (signal 4)**, self-crash during early init; illegal-instruction cause unresolved | NOT lmkd/memmgr; AMS `OnRemoteDied` is post-death | **NO** (no Realm/SlabAlloc trace) | 0 — 搁置 (resolve the SIGILL first) |
| toutiao | **disappeared, UNKNOWN** — hilog capture ended before the exit | none captured (no lmkd/kill/signal/ANR in-window) | NO | 0 — 搁置 (re-run with longer capture) |
Neither folds into sysconf. mcdonalds is upgraded from "unknown" to "SIGILL (unresolved)"; toutiao stays genuinely unknown
(a capture-window artifact, not a mystery kill).
