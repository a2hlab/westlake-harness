# Toutiao on the source-built runtime, on three fresh boards

Toutiao 13.9.0 (`a1112a0c…`) launched on three DAYU600 boards freshly flashed with OpenHarmony 6.1.0.31
(47/47 firmware libraries match `native/oh61-firmware-abi.json`), running the runtime built from Westlake
`22b9453` through the manifest source closure. One question: what stands between "shows its chrome" and
"usable" — real headlines, scrolls, opens an article, stays alive.

Status on 2026-09-25: rows 1–6 fixed — Toutiao passes consent, avoids the WebView crash, boots Cronet, and renders
23 real headlines. But it is **not yet interactive**: feed items don't open, tabs don't switch, and real touch is
not consumed (row 7, open). An earlier "interactive" claim here was wrong and was retracted once the operator tried
it by hand. Each layer was hidden behind the one before it.

## What stood in the way

| # | Symptom | Cause | State |
|---|---|---|---|
| 1 | Screens black, taps do nothing | Fresh board: clock at 1970, 30 s screen-off drops the lock screen over the app, OH backgrounds the host so the app's sub-windows go 0×0 | Board setup (`board_setup.sh`, `baseline_run.sh` re-fronts the host) |
| 2 | Consent dialog ignores taps | Screen → window coordinates never converted; the 1200×1790 dialog is centred in 1920, so every tap lands 65 px low. Root choice also preferred the focused activity over the dialog | **Fixed** — Westlake `5e91ebc` (board #8), verified: screen-coordinate `c 600 1272` closes the dialog with automatic root choice |
| 3 | Consent passes, then the process dies 10–300 s later | Consent starts the WebView. Chromium 109's `gfx::SurfaceControl::IsSupported()` CHECKs that the whole NDK `ASurfaceControl`/`ASurfaceTransaction` table resolves once `SDK_INT >= 29` (Westlake reports 34), *before* it reads the `AndroidSurfaceControl` feature. The source-profile WebView `libandroid.so` exported none of it, so `brk #0` at file `0x170531c` on `CrBrowserMain`. Disabling the feature (board #10) cannot help | **Fixed** — Westlake `e88df46` (board #17): the 22 entry points as logged no-ops; none is ever called. 0 crashes after consent vs 6/6 before (pmproc 2/2, integrated build 3/3, same board 1/1); independent re-run by a second agent pending (board #18) |
| 6 | Survives consent, full chrome, the feed stays blank | TTNet's Cronet never boots: `libsscronet.so` imports bionic-only symbols (`__sF`, `__errno`, `android_fdsan_exchange_owner_tag`, bionic-layout `getaddrinfo`) but was not an Android-ABI target, so every load failed (204 attempts, never mapped). TTNet swallows the error; `CronetInit` waits on `sWaitForLibLoad` forever, and with neither success nor failure recorded TTNet never falls back to OkHttp | **Fixed without code** — launch with `--android-native-target libsscronet.so --android-native-net-target libsscronet.so` (the network-structure translator from manifest `f229702`, never run on a board before). Cronet `bootSucceed` 0 → 1; **the feed then loads 23 real headlines** with 55 TLS handshakes to Toutiao's own CDNs. See [`toutiao-feed-loaded.jpeg`](toutiao-feed-loaded.jpeg) |
| 7 | Feed and tabs render but don't respond to touch | The Toutiao activity window draws under the OH host but never becomes input-eligible: the whole tree reports no focus (`f=1` appears 0 times) and content nodes have `windowVis=0`. A real DOWN/UP (`i` command, `dispatchSingleTouchViaViewRoot`) returns `down=0 up=0` — delivered to the DecorView, consumed by nothing. `performClick` (`c`) worked on the consent dialog only because it bypasses the input pipeline; feed scroll, item-open and tab-switch all need real gesture consumption | **Open** — board #20. `aa start` re-fronting restores drawing, not window input focus. This is the "cannot interact" the goal names, and it is distinct from the #8 consent-touch fix |
| 4 | Exits after 60–120 s, any build, with or without network | The Android-visible process name was the host's. `TokenUtils.a` (ByteDance token SDK) reads `/proc/<pid>/cmdline` = `appspawn-x …`, decides "not the main process", and `TokenObjectProvider` forwards every query to itself — 194,500 cycles until the 32 MB stack is gone | **Fixed** — `19fb4c2` (board #11): argv block rewrite + AOSP comm rule + `setArgV0` at bind. Verified: cmdline `com.ss.android.article.news`, comm `id.article.news`, `TokenObjectProvider.query` = 0 |
| 5 | Still exits after 62–200 s | The same token self-forwarding as row 4, through the fourth channel: `PackageManager.getApplicationInfo(pkg).processName` was null for a manifest that omits it. The recursion is JIT-compiled and logs nothing; the ART GC root scan (`LocalReferenceTable::VisitRoots`) is only the frame that crosses the stack edge | **Fixed** — `2478a7f` (board #12): the PM registry normalizes an omitted `processName` to the package name. Verified independently: 332 s untouched, deepest app thread flat at 4.4 MB, no crash |

Noice 2.5.1 and Wikipedia reach their first screens on the same stages throughout — every one of these is
Toutiao-specific or load-specific, not a broken runtime.

## Evidence

- [`crash-chains.txt`](crash-chains.txt) — the three crash chains, symbolized, with the offset rules that make it possible.
- [`stack-depth-samples.txt`](stack-depth-samples.txt) — per-thread stack depth every 8 s until death: several threads fill 32 MB concurrently.
- [`acceptance-baseline.json`](acceptance-baseline.json) — the "usable" acceptance on the original build: no headline, no scroll, dead at 195 s.
- [`netcap-consent-pmproc.txt`](netcap-consent-pmproc.txt) — what went on the wire across the consent tap: the feed
  host is asked for and handshaken, then the row-3 crash, so an empty feed here is not a request that was never sent.
- [`recursion-ring.txt`](recursion-ring.txt) — the JIT-code return-address histogram that turned row 5 from "a GC bug"
  into row 4 again.
- [`cronet-hang.txt`](cronet-hang.txt) — row 6: the Cronet state probe before and after the launch targets, and the
  `CronetInit` thread parked on the library-load `ConditionVariable`.
- Fix reports live with the fixes: `westlake-touchfix/TOUCH-WINDOW-OFFSET-8.md`, `WEBVIEW-GPU-10.md`,
  `westlake-procname-cx/PROCESS-IDENTITY-11.md` (Westlake worktrees in VM `a2hlab`).

## What this run got wrong first

Two conclusions were drawn from one sample each and had to be withdrawn:

- **"Network fixes the self-exit."** One untouched run on a networked board survived 240 s; the next died at 90 s.
  Toutiao's startup is non-deterministic (the bring-up handoff calls it a launch lottery). Take at least two samples
  before comparing builds, flags or network states.
- **"The WebView fix removes the crash."** The same flag gave zero `ASurfaceControl` errors in one launch and 22 plus
  the `SIGTRAP` in another.

- **"The feed renders."** The view tree had `FeedCommonRecyclerView` and the tab bar; it had zero article rows. A
  container is not content — count the rows.

- **"`--disable-features=AndroidSurfaceControl` removes the WebView crash."** The flag reached Chromium
  (`[SOURCE-WEBVIEW-CMD]` in every log) and the crash stayed at the same pc 3/3. The missing symbols were the cause;
  the feature switch was never on the path. The source comment that kept `ASurfaceControl` out of the shim ("Chromium
  treats a partial table as usable") had the same wrong premise: on API ≥ 29 an absent table is a CHECK, not a fallback.
- **Two crash mechanisms were proposed and withdrawn the same hour**: WebView's renderer-gone terminator, and
  appspawn-x's inherited `waitpid(-1)` SIGCHLD handler stealing Chromium's child status. The handler that `sigaction #16`
  restored after the crash was the one installed at startup (#2): the child that exited was Chromium's crash
  collector, forked *after* the `brk`. Read the order of events before the events.
- **The transport was checked again.** The 2026-09-23 record says, in so many words, not to re-derive connectivity; a
  capture and a flow table were built anyway before reading it. The answer was in the app's own state (`N` probe, a
  SIGQUIT dump), not on the wire.

And one mistake of diagnosis, not sampling: the WiFi failure looked like a MAC allowlist (`ASSOC-REJECT` 16 while the
Mac connected). It was signal — the boards saw the access point at −90 dBm.

## Rules this adds

1. **The Android-visible process identity is a platform contract.** SDKs decide "main process" from
   `Application.getProcessName()`, `ActivityThread`, `/proc/self/cmdline` and `getRunningAppProcesses()`, in that
   order, and act on the answer. Every channel must equal `ApplicationInfo.processName`; the OH sandbox identity
   (bundle, uid) is a separate thing and stays as it is.
2. **A fault in a GC checkpoint is not necessarily a GC bug.** Look at `sp` against the thread's stack mapping first:
   at the bottom of the mapping means the stack was already spent.
3. **Measure stack depth from outside** when no Java stack is available: `/proc/<pid>/task/*/syscall` carries each
   blocked thread's `sp`; `stack_depth_sampler.py` turns it into depth over time.
4. **A fixed layer exposes the next.** Each of rows 3–6 was invisible until the row before it was fixed.
5. **Export the whole NDK table for the API level you report.** Chromium decides from `SDK_INT`, not from what it can
   find; a shim that omits an API-29 table on a runtime reporting 34 is a crash, and no-ops are enough to pass.
6. **A DSO that imports bionic-only symbols usually needs to be an Android-ABI target** (and a network target if it
   takes bionic-layout `addrinfo`). The candidate list can be derived from undefined symbols, but a derived list is a
   hypothesis, not a result: forcing `libmetasec_ml.so` into the Android-ABI namespace crashed it inside its own
   code, and the fully derived list for Toutiao (124 native + 9 net targets, vs 3 hand-picked) coincided with Toutiao
   failing every stage in the 100-app rescan. Verify each derived target by loading it on the board before relying
   on it.
7. **A load that neither succeeds nor fails is a hang, not an error.** When nothing is logged, look for waiters: an
   ART thread dump via SIGQUIT (the Signal Catcher is present; SIGQUIT is blocked on app threads) names the
   `ConditionVariable` everyone is parked on.

## Tools added in `westlake-inputs/tools/` (VM-side launcher glue, not part of this repo)

`hdc_mac.sh` (hdc from the VM through the Mac), `board_setup.sh`, `baseline_run.sh`, `ttdrive.sh`
(`front`/`vt`/`tap`/`consent`/`shot`), `toutiao_accept.sh` (the usable-acceptance, one JSON line),
`stack_depth_sampler.py`.
