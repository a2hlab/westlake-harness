# #38: physical input consumption and visibility

**Blocked on <2s visible OH article-page acceptance; R2=partially.** Phase ACK already appended; CPU profiles and comparison evidence are included below. Branch `feat/ability-focus-38`, board `5ea34a4500000000000000001123012c`. The only additional device is the explicitly authorized Android reference `N100CU025C18D000128`.

The frozen source base is #34 `237f1e5`; deployment is #14/out-touch21-wake + out-sp20, sscronet native/net parameters and the #30 image native targets. No out-all0925, #16/#23, system partition writes, skipped certificate verification, symbol shims, or push. #28's lock fix is not silently folded into this base.

## Changes and limits

- `79875b9`: resume/stop calls the real `ViewRootImpl.mWindow.dispatchAppVisibility` on the main Looper for the exact Activity token. Direct `activityResumed` is covered. No direct field write is added. Visibility-1 proved **mAppVisible was already true before and after**; the proposed false-visibility explanation does not explain that first-feed trial.
- `49e1598`: bridge the exact Android root's NOT_FOCUSABLE / NOT_TOUCHABLE flags into OH session properties. DimLayer had flags `0x1000318` but previously acquired a touchable OH region. MMI subsequently selected the main window. Zero-width popups are clamped to the minimum OH extent instead of expanded across the display. GetAgentWindowId remains authoritative; no self hit-testing or rerouting.
- `2ac9009`: diagnostic-only uptime markers at receive, Java main dispatch, DecorView return, native finish, the existing ViewGroup touch-target chain, performClick, startActivity and activityResumed; main-thread stack sampling after DOWN. This instrumented build is not a production performance tuning change.
- `ffff3cf`, `3691e32`: persist stack probes to stderr and select the main Looper thread directly, since attached launch threads have unstable names.

These commits **do not create an OH AbilityRecord**. Existing AttachApplication IPC is not proof that AMS knows the directly spawned process. Hanbin's documented touch hit-test independence from focus also means failed article navigation alone does not establish an AMS root cause.

## What the early trials actually show

| Trial | Observation | Acceptance |
|---|---|---|
| visibility-1 | mAppVisible true/true; uinput routed to DimLayer; no anchored detail ENTRY in ~10s | Fail |
| policy-1 | MMI routed to MainActivity, native receive succeeded; no anchored detail ENTRY in ~10s | Fail; short observation cannot prove never-clicked |
| trace-1 | queue 10,438 / 10,809ms; real line-start NewDetailActivity ENTRY at +26.01s, followed by transaction execution | Fail; screenshot remained feed, not article |
| trace-2 | queue 8,666 / 9,467ms; DOWN dispatch 665ms; both finish handled=1; actual target chain reached FeedItemRootLinerLayout | Diagnostic only: before screenshot was host |
| timeline-1 | No acceptance touch before visible-feed preparation timed out | Invalid trial |
| timeline-2 | 45s observation, but screen locking/preparation issues and no qualifying input chain | Invalid trial |
| idle-a1 / cold-a1 | Earlier stack probe could not identify the actual main thread | Invalid idle precondition |
| cold-a2 | Authoritative stacks obtained; null-Looper main-thread failure before idle acceptance | Startup blocked |
| warm-b1 / warm-b2 / warm-b3 | Earlier harness retained old VT lines and could re-select obsolete consent; login/host frames are excluded | Not valid warm article samples |

The old files named `after-2s` in visibility-1/policy-1/trace-1 mean two seconds **after the polling window**, not two seconds after input. They are retained unchanged and are not used as 2s evidence. The current script schedules screenshots from input completion and logs device uptime for each capture. Filenames alone are never timing proof.

The VT helper now snapshots the child log line count before each request and reads only newly appended lines. Physical article samples use `uinput -T -d 380 297 -u 380 297`; consent uinput is labeled SETUP_ONLY. Earlier i/c consent and mistaken stale-consent actions remain explicitly recorded. Settings JSON containing Activity names is never lifecycle evidence; lifecycle parsing is anchored to producer lines.

## Idle cold / retained-data comparisons

Three visually reviewed, unobstructed-feed article-target cold samples reached the authoritative main Looper's `nativePollOnce` before input:

| Trial | DOWN/UP queue ms | DOWN/UP dispatch ms | startActivity ms | subsequent detail RESUMED ms | 2s screenshot |
|---|---:|---:|---:|---:|---|
| cold-a4 | 63 / 180 | 124 / 58 | 1231 | 15103 | feed |
| cold-a5 | 20 / 127 | 111 / 53 | 1219 | 14858 | feed |
| cold-a7 | 20 / 223 | 207 / 49 | 1033 | 17251 | feed |
| warm-b8 (re-consent) | 154 / 266 | 116 / 55 | 1374 | 20815 | feed |
| warm-b10 (re-consent) | 34 / 282 | 238 / 12 | 1038 | 20550 | feed |

All deltas start at device `/proc/uptime` INPUT_BEFORE, not host wall clock. The measured queue is the bridge's main-handler post delay. `RESUMED` itself logs a token; it is associated here with the immediately preceding exact component B47 transaction and the new detail root, not a settings-JSON substring. A RESUMED callback alone is insufficient for visible-article acceptance.

cold-a4 has a faultlog-proven RenderThread SIGSEGV at NULL, `libwebviewchromium.so+0x3e026f0`, besides the stderr SIGABRT line. At 45s the app is gone. Do not report a clean run from stderr alone. No new ICU crash is asserted without a corresponding fault stack; older #30 ICU faults are not silently treated as resolved.

Warm preparation remains problematic: warm-b7 preserved app data but the actual before screenshot again showed consent (and the host keyboard); its touch is not an article sample. This also corrects the tentative claim that all repeated-consent sightings were merely stale VT. warm-b1/b2/b3 were additionally affected by the old VT-tail script and are excluded. Later retained-data trials that need consent again must be labeled **re-consent**, not an initialization-free warm-start comparison.

cold-a6 is a third independent physical dispatch observation (queue 41/153ms, dispatch 108/8ms), but dynamic feed content/geometry led to TikTokActivity; it is excluded from the NewDetailActivity table. warm-b9 and warm-b11 exited before the test. warm-b9 records ART’s `No pending exception expected` with an IWebViewUpdateService null receiver during CookieManager/WebView provider initialization; warm-b11’s saved tail ends around WebView native loading without a captured fault stack, so its cause remains unknown. No three-sample initialization-free warm cohort is claimed. Fixed coordinates were replaced in a7/b10 by a title-derived physical coordinate; their raw selected-title text metadata has a regex capture error, while the rect/coordinates and selection VT remain available for review. The regex is now restricted to a single line; original evidence is unchanged.

## Transaction / CPU / crash findings

See [CPU_PROFILE.md](CPU_PROFILE.md), [CRASHES.md](CRASHES.md), `cpu-summary.json` and `crash-classification.json`.

The complete child logs **do contain** `[B47-SLA] AFTER executeTransaction SYNC OK`: cold-a4 L60733, cold-a5 L61826, warm-b8 L50882. Their after-45s lifecycle extracts also contain it. The earlier external conclusion that all three never reached AFTER conflicts with these originals. Source AppSchedulerBridge.java:1960 executes the stock transaction synchronously under `WL_SYNC_TRANSACTION`, despite the preceding diagnostic saying “BEFORE scheduleTransaction”; a separate resume transaction follows. This does not establish a visible article page.

Java samples within that interval show activity construction, NewDetailActivity.onCreate, WebView/JS bridge initialization, layout inflation and comment widget construction; later samples show fragment/resume setup. In the separate cpu-detail-1 profile, +2.143s is AwContents/WebContents construction, +4.162s LayoutInflater, +6.168s preloadFragment, +8.185s nativePollOnce, +10.185s WebView NavigationController and +12.193s article fragment work. Therefore this is executing launch/resume work, not an untouched transaction queued behind WMS.

The CPU-only runs use task-clock at 400Hz with call graphs and are **excluded from all latency n**. Android consent: 10.014s, 10,157 total samples, zero lost, main 1135 samples / 2837.5ms. OH consent-2: 10s, 7814 process samples, zero lost, main 644 periods / 1610ms. Both have direct nterp leaf samples; OH also has zygote-JIT and anonymous executable samples. OH main self time includes 592.5ms locks/synchronization (art_quick_lock_object 327.5ms, MonitorEnter 192.5ms), 227.5ms class loading/verification/resolution. **This does not support treating OH as always ExecuteSwitchImplCpp or all interpretation.** Limited samples cannot prove a path never executes.

Consent-window main CPU ratio is 0.567x OH/Android, not a causal decomposition of the earlier 665ms DOWN delay. Equal wall windows contain different work and off-CPU waits. The report gives additive category contributions to this measured CPU ratio and explicitly leaves the original dispatch factor unexplained. Separately, OH detail sampling stopped when the app exited after 16.002s (requested20s), 12,689 total samples, zero lost: main2662.5ms, RenderThread130ms (52 periods, too few to infer detailed rendering cost). Main self: locks682.5ms, class/verification/resolution587.5ms; call chains include reflection→ClassLinker→MethodVerifier and page faults→down_read/rwsem. Kernel and profiler overhead, anonymous JIT symbols, waiting and differing SoCs limit cross-device causal claims. No unsupported 150x explanation is offered.

OH consent-1 failed to accept a symbol directory under app-private storage and produced no perf.data; its misleading command RC0 is retained, but no CPU result is claimed. Retry used the identical public stage's symbol files and verified actual data/sample counts. `kptr_restrict` was restored to1 by hiperf; ftrace remained nop/tracing_on0. Android adbd was temporarily rooted for simpleperf, then unrooted by the script.

All stderr Fatal banners are separately classified by emitting thread, register PC/LR, available same-run maps and OH faultlogs. Two same-run maps (a4 and cpu-detail-1) resolve work_thread SIGABRT's PC to musl+0x96f1c and LR to libnpth+0x13854. Disassembly shows signal re-delivery via syscall240; that is the crash-handler site, not the original fault cause. Other missing backtraces/DSOs stay unknown. The app-process RenderThread SIGSEGV in a4 is a separate event. Main null-Looper exits and historical ICU faults are not conflated with either group.

## Cleanup and remaining gaps

No test app, appspawn-x, work_thread or hiperf remained in the final OH process query. Android has no app/simpleperf process and adbd is back to shell uid2000. OH kptr_restrict=1, current_tracer=nop and tracing_on=0. The screen keep-on lock is inactive and the board reached SLEEP. `power-shell timeout -r` reported failure; the authoritative final dump shows ScreenOffTime Timeout=30000ms / OverrideTimeout=10000ms, not the experiment’s one-hour override. The original override was not captured, so exact restoration of that setting is **not verified**. See evidence/cleanup.

The profiler captured endpoint main-thread CPU IDs (OH 2→7, Android 5→4), not continuous CPU residency or matching clock-frequency samples. CPU-frequency-normalized causal decomposition, off-CPU waits and the original 665ms event’s CPU attribution remain unverified. Warm article samples remain n=2 with re-consent, below the requested n≥3. The next useful work is controlled off-CPU/clock sampling of the detail initialization interval and independent reproduction of the WebView null crash; repeating input routing changes is not supported by this evidence.

## Android reference

Same unmodified APK SHA256 `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`, version 13.9.0/13900, Android 16, 1200x1920. Fresh data, actual consent, then input tap at ~30s. **Android input tap is a reference path; it is not presented as OH uinput.**

`android-summary.json` is generated by `scripts/analyze_android38.py`, which pairs atrace event cookies and requires an exact `wm_on_resume_called` detail-component record.

| Trial | Receive→deliver DOWN / UP (ms) | deliver S→F DOWN / UP (ms) | INPUT_BEFORE→detail onResume (ms) |
|---|---:|---:|---:|
| c2 | 0.814 / 0.086 | 3.710 / 2.704 | 896 |
| c3 | 1.363 / 0.132 | 5.273 / 3.716 | 610 |
| c4 | 1.466 / 0.329 | 5.240 / 3.429 | 647 |

Android receive→deliver is the interval from the native InputConsumer processing trace to ViewRoot delivery, not an added Java Handler queue. Event age is also retained in JSON. It is not strictly identical to OH's worker-post→main-runnable queueMs. All three have article title/header screenshots; c4's image area was still loading at ~2s. c1 is supplemental: trace-buffer wrapping lost one event's beginning, so it is excluded from paired timing statistics.

## Reproduction and evidence

All VM commands must be entered through `orb -m a2hlab bash -lc '<cmd>'`. The scripts are on the host-mounted worktree path; board34.py binds the sole OH serial. Builds replay only changed compilation units and relink their owning DSO. Adapter/framework dex changes require regenerating the matching boot-image group. No native-runtime full-chain rebuild is used by the final helpers. An early isolated broader #34 rebuild was abandoned and not deployed.

Current stage: `/data/local/tmp/a2hlab-framework-ability38-v7`. The accepted #34 transport DSO and runtime are retained except for explicit diagnostic runtime logging. Java/framework diagnostics are separately identified in the build reports. Runtime upgrade only replaces bridge while no process namespace is live; before/after hashes are recorded.

Raw evidence uses deterministic gzip where useful, with SHA256 of both stored bytes and decompressed originals. Run `python3 benchmark/2026-09-25-ability-focus/verify.py --git` after committing. VM originals remain under `~/a2hlab/board/5ea34a4500000000000000001123012c/ability38/`.

R2 is **partially**: source/build/preload, physical click consumption, cold n=3 article-target timing, Android reference n=3 and CPU evidence are verified within the stated instrumentation limits. Visible article <2s, a qualifying warm n≥3, tab/scroll and full control-app regressions are not accepted. No OH screenshot is presented as a successful article page.
