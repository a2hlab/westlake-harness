# Toutiao M4 "never created a window session" — it is SLOW (JIT off), not WAITING on a service

Offline, no board. The dispatch (board #90, 2026-10-02 21:05): for U10.1T8 stage-A toutiao (5ea window1, 61b window5),
answer statically + from logs — (1) where is the main thread stuck at t20, slow or waiting (lock/binder/net/file);
(2) if slow, estimate time-to-`createSession` and whether a t60 screenshot window can prove it; (3) if waiting, which
service/call and what we lack. Then give the minimal fix + its layer, or a ≤30-min default-disabled board experiment.

## TL;DR
**Slow, not waiting.** Toutiao's Java main thread grinds through `ActivityThread.handleBindApplication` — bytedance's
multi-framework init (Mira plugins + Tinker + RouteMonitor + hundreds of projected PackageManager/ServiceManager calls)
— in the **ART interpreter with JIT disabled** (`APPSPAWNX_NO_JIT=1`). No single lock/binder/network/file stall: 12.79 s
of continuous progress with exactly one 3.26 s quiet that self-resolved. It never reaches `callApplicationOnCreate` in
the clean capture, so it is **nowhere near** the app window session. The lever is the runtime (JIT/AOT), not a stubbed
service.

## Two corrections to the premise (evidence-first)
1. **There is no t20 capture for toutiao.** The clean 61b window5 run (PID 10020) has **only `maps-t5`, no `maps-t20`**;
   its hilog ends at **t+15.5 s** (17:08:40.2 → 17:08:55.7). So "stuck at t20" is answered at the last captured instant
   (~t+15 s), not t20. **5ea window1 has no toutiao launch trace at all** — the only 5ea toutiao dir
   (`window/boards/u101-t8-A1-r2.../5ea/.../toutiao-gain/`) is install-only (no `hilog.txt`). So the usable evidence is
   the 61b window5 clean run + the 61b stageB-final retest (dirty, `batch_interrupted`).
2. **"WindowSessionAdapter created" is NOT the app window session.** window5 logs
   `OH_WSAdapter: WindowSessionAdapter created, ohSession=0x7f313e1f28` at t+1.7 s — that is the route-A shim's own
   OH-side session handle, created early during `WMClient.connect`. The *app* window session (ViewRootImpl →
   `IWindowSession` → relayout → a Surface with content) requires an Activity + `addView`, which never happens.
   `white-keys.csv`'s `no_window_session=True` is about the latter; it is consistent with never reaching an Activity.

## (1) Where it is stuck, and slow-vs-waiting — SLOW

The BIGSTACK thread model is the key to reading this: the native launcher (tid == PID) spawns an 8 MB-stack pthread to
run `ActivityThread.main`, then `DetachCurrentThread` and exits. So the launcher tid dies at t+0.7 s and the **real Java
main thread is a different tid** (10032 in window5, 3989 in stageB). Reading only the PID==TID line misreads "main
thread exited early."

window5 Java-main (tid 10032), from `evidence/window5-61b-timeline.txt`:
| t (rel 17:08:40.2) | event |
|---|---|
| t+0.4 s | `ART JIT DISABLED via APPSPAWNX_NO_JIT=1` |
| t+0.7 s | launcher `[CM-BIGSTACK] DetachCurrentThread before join`; Java main = tid 10032 |
| t+1.3 s | `Launching android.app.ActivityThread.main()` |
| t+1.3 s | `ScheduleLaunchApplication -> bindApplication: bundle=com.ss.android.article.news recordId=878` |
| t+11.8 s | logged stack still at `handleBindApplication(ActivityThread.java:6976)`; `Content provider … already published` (Mira `PluginPackageManagerProvider`, Tinker `StubContentProvider`) |
| t+13.5 s (last 10032 line) | `[B8-PM] projected getProviderInfo …dataplatform` / `getServiceInfo …agconnect` — still in `installContentProviders` |

**Slow, not waiting**, by the gap test: tid 10032 emits **477 lines over a 12.79 s span** with **exactly one gap ≥1 s
(3.26 s, 17:08:42.17→45.43)**, and that quiet **self-resolved** (it resumed with display/colorspace queries). Both
sides of the 3.26 s quiet are fast `getService(...)→null` stubs — not a binder block. Time-sink categorization of tid
10032: **315 `AppSpawnXJava`** (stderr-forwarded Java: `[B8-PM]`/`[G2.5-PIB]`/`[OHServiceManager]`/Mira) + **92
`OH_Parcel`** marshals. That is CPU-bound compat projection in the interpreter, not a stall. (`evidence/churn-and-jit.txt`.)

The app is `com.ss.android.article.news` / `ArticleApplication`; `callApplicationOnCreate` / `handleLaunchActivity` /
`callActivityOnCreate` count = **0** in window5 → it never even starts `Application.onCreate`; it is stuck *before* that,
in `handleBindApplication` → `installContentProviders`.

Corroboration from the dirty stageB retest (PID 3969, tid 3989; `evidence/stageb-61b-oncreate-sigsegv.txt`): same
JIT-off, but it progressed **further** — `attachBaseContext` (Mira/Tinker) ate t0→**t+11.6 s**, then
`ArticleApplication.onCreate` is reached at **~t+15.2 s** via
`callApplicationOnCreate ← RouteInstrumentation ← MiraInstrumentation`. So on a good run onCreate *starts* around
t+15 s — but `attachBaseContext` alone costs ~12 s, which pins the slowness on bytedance's framework init under the
interpreter.

## (2) If slow — time-to-createSession estimate, and can a t60 window prove it
Budget from the traces (JIT off, interpreter):
- `attachBaseContext` (Mira plugin framework + Tinker): **~12 s** (stageB t0→t+11.6 s).
- `installContentProviders`: window5 is still in it at t+13.5 s (several more seconds).
- `ArticleApplication.onCreate`: *starts* ~t+15 s (stageB). This is Toutiao's heaviest phase (SDK/plugin/network init);
  on a JIT-less interpreter it is realistically **many tens of seconds**, not seconds.
- Then first Activity → `setContentView` → ViewRootImpl → the real window session, *after* onCreate.

So `createSession` is **well beyond 60 s** — onCreate has not finished at t+15 s in the better run, and the window phase
is after onCreate. **A t60 window cannot prove lit**; it can only prove *progress* (if by t60 it has advanced past
`installContentProviders` into onCreate / an Activity). To actually settle slow-vs-stuck and bound the time, a **t120**
(or longer) capture is needed — see the experiment.

## (3) If waiting — what we lack (secondary; nothing blocks)
Nothing blocks, but for completeness: **20 distinct system services resolve to `null` stubs**
(`getService("connectivity"/"power"/"notification"/"network_management"/"appops"/… )→ null (stub)`), and Mira's
`PluginPackageManager.getApplicationInfo` hit **1** `null object` (caught by `plugin_exception_monitor`, non-fatal).
Each stub returns in <1 ms; none stalls. The risk is only indirect: a bytedance SDK that *retries* on a null service
adds interpreter churn. The repeated **32 `[G2.5-PIB] ApplicationInfo … zeroed`** for the same package across worker
threads is likewise cacheable churn, not a wait.

## Minimal fix + layer
- **Primary lever — runtime (JIT/AOT).** `APPSPAWNX_NO_JIT=1` is the structural cause: every one of bytedance's
  framework-init bytecodes runs interpreted. Re-enabling ART JIT (or AOT-compiling the app dex) is the real fix for
  "too slow." **Caveat:** route-A disabled JIT deliberately (stability); this is a runtime change with known risk, not a
  free toggle — it must be gated behind the experiment below and a single-variable window, owned by the runtime/appspawn-x
  lineage. Layer: `liboh_android_runtime.so` / appspawn-x env, **not** a per-app or JAR change.
- **Cheaper compat-layer mitigation (does not fix the floor).** Cache the repeated projected `ApplicationInfo` /
  `getProviderInfo` / `getServiceInfo` results (32 re-zeroed ApplicationInfo + 92 Parcel marshals on one thread) in the
  B8-PM / G2.5-PIB projection so each query does not re-marshal an `OH_Parcel`. Layer: the compat projection in
  `liboh_adapter_bridge.so` / the `[B8-PM]`/`[G2.5-PIB]` path. This trims churn but does not change the interpreter floor;
  only worth it if the experiment shows the projection cost is a large fraction of the budget.

Because toutiao never reaches a window in any captured trace, **no fix is asserted to "build a session"** this round;
the honest deliverable is the slow-vs-waiting verdict + the lever + a falsifiable experiment to bound it.

## This round's rule
Read the Java main thread by the **BIGSTACK tid** (the detached 8 MB-stack pthread), not the PID==TID launcher line.
Decide slow-vs-waiting by the **largest silent gap on that tid**, not by whether logs exist: continuous progress with a
self-resolving sub-second–to–few-second quiet = slow; a multi-second silent park on one call = waiting. And do not infer
t20 state when **only `maps-t5` exists** — say "last captured instant," count captures from `facts.txt`.

## Files
- `evidence/window5-61b-timeline.txt` — clean run: JIT-off, BIGSTACK handoff, the 3.26 s gap, the stuck phase, 0 onCreate.
- `evidence/stageb-61b-oncreate-sigsegv.txt` — dirty retest: onCreate reached ~t+15 s + handled-SIGSEGV open flag.
- `evidence/churn-and-jit.txt` — JIT-disabled line, tid-10032 time-sink categorization, churn counts, getService stubs.
- `experiment/t120-extended-capture.md` — the ≤30-min default-disabled extended-capture window + pass/fail criteria.
