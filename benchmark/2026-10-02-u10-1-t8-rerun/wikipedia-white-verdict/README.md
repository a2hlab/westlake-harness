# Wikipedia white in the U10.1-T8 window (5cd) — verdict: A (render white lottery), NOT B (T8)

**Question** (offline, read-only): the U10.1-T8 promotion window r2 showed Wikipedia **pure white** at t20 on 5cd
(U9 signed = lit; U10.1 both windows without T8, 5cd original = lit), and cx-t0 conservatively stopped on the
lit-key regression. Is this **A** = the pre-existing white lottery (sessions_ / bridge-runtime double-copy, the
N11h target) or **B** = a T8 regression (T8's `com.android.org.conscrypt.SSLParametersImpl` presence stub changing
Wikipedia's OkHttp platform selection)?

## Verdict: **A (render-side white lottery / double-copy, N11h target). B (T8) is decisively refuted.**

## Evidence

### 1. The two t20 screenshots — identical inputs, opposite render outcome
- `wikipedia-t20-t8window-5cd-WHITE.jpeg` (T8 window r2, run `20261002T133745-0de824c1`): **pure white** — no Wikipedia
  shell at all, only the OS status bar + nav bar.
- `wikipedia-t20-u101-noT8-5cd-LIT.jpeg` (U10.1 no-T8 window, run `20261002T015250-3a49eae2`, same board 5cd):
  the **Wikipedia welcome page fully rendered** ("WIKIPEDIA", 全世界的知识, the intro text, the globe logo).

The welcome/onboarding page is **local app content — it needs no network**. One run drew it, the other drew nothing.

### 2. Network behaviour is identical in BOTH runs (so network is not the discriminator, and is irrelevant to the welcome page)
Both hilogs show the same OkHttp failure fetching the feed:
`java.net.SocketTimeoutException: failed to connect to zh.wikipedia.org/2001::1 (port 443) ... after 10000ms`
(suppressed: `.../31.13.94.10`). `zh.wikipedia.org` DNS-resolves to unreachable/poisoned IPs (`2001::1` reserved,
`31.13.94.10` is a Meta/Facebook range) on the board's CN wifi — a GFW/DNS environment issue, **the same in the lit
run**. Counts: white run SocketTimeout x6 / connectSocket-err x3; lit run SocketTimeout x6 / connectSocket-err x3.
The failure is a **TCP connect timeout (`IoBridge.connectErrno` -> `PlainSocketImpl.socketConnect`)**, i.e. BEFORE any
TLS / OkHttp platform selection. The welcome page renders without it.

### 3. Both runs: alive, no fatal, render pipeline active
White run: VSync 2379, Surface 3943, bindApplication, MainActivity theme resolved, **0 FATAL / 0 SIGSEGV**.
Lit run: VSync 2355, Surface 3297, 0 FATAL. So in both the app is alive and the render loop is ticking; the only
difference is whether the first frame reached the **visible** surface — the signature of the render / sessions_
double-copy lottery (A).

### 4. The double-copy substrate (what N11h targets) is present
White run `maps-t5-16137.txt`: `liboh_adapter_bridge.so` = 2 r-xp load bases (7ef5db8000, 7efe438000),
`liboh_android_runtime.so` = 2 (7ee2b2d000, 7ef5f2d000); `libart.so` / `libopenjdkjvm.so` = 1 each. This is the
U9/U10.1 double-copy that N11h is designed to collapse to 1 — the mechanism behind the render lottery.

### 5. T8 is refuted — Wikipedia's OkHttp never consults SSLParametersImpl
- **The Wikipedia APK (eba82a0f) references `SSLParametersImpl` 0 times** (dexdump of all classes.dex AND a raw
  byte grep of the dex = 0; `conscrypt` 0; `android/net/ssl/SSLSockets` 0 as a type ref). It has
  `okhttp3.internal.platform.Android10Platform` (27) and `AndroidPlatform` (61). So Wikipedia's OkHttp does **not**
  do `Class.forName("com.android.org.conscrypt.SSLParametersImpl")` — that Class.forName lives in OkHttp's
  `ConscryptPlatform.buildIfSupported`, which Wikipedia's R8-minified OkHttp does not include. **T8's presence stub
  is never looked up by Wikipedia** → it cannot change Wikipedia's platform selection. (The SSLParametersImpl
  consumer is toutiao's hardened OkHttp, not Wikipedia — the outer's static premise conflated the two.)
- `SSLParametersImpl` appears **0 times in both hilogs**; OkHttp uses the `[B8-TLS] Westlake SSLContext` path
  (unchanged by T8). The one `conscrypt` line is a B8 JAR-verify provider swap, unrelated to platform selection.
- T8 changes only three BCP-jar items (conscrypt presence stub, real libphonenumber, getInstallSourceInfo) — none
  touch rendering, surfaces, sessions_, or sockets.
- The lit comparison run was built **without T8** and behaved identically (same network timeout, same render
  pipeline) yet rendered — so the lit/white difference is not T8.

## Consequence
The Wikipedia white in the U10.1-T8 window is the **pre-existing render white lottery** (wikipedia is a known flaky
key, EVO-0051), not a T8 regression. The conservative lit-key-regression stop was triggered by a **flaky key**, not
by T8. T8 is not implicated in this white. The real fix for Wikipedia's flaky white is **N11h** (single bridge/runtime
load base → deterministic surface binding); it is not a T8 concern.

## If further confirmation is wanted (A/B already decided; this would only re-confirm A)
N11h's own 61b window is the A-confirmation experiment: with single-copy (N11h), Wikipedia's first frame should draw
deterministically. A cheaper direct re-confirmation without N11h: relaunch Wikipedia on 5cd under the **current T8
candidate** N times (e.g. N=10, `--launch-only`, t20 each) and under **U9** N times; if both bases show the same
non-zero white rate (lottery, independent of base), A is confirmed and T8 adds no white. (Use a reachable mirror or
ignore the feed — the welcome page is local, so the lottery shows on the first frame regardless of network.)

## Evidence sources (read-only, not copied except the two t20)
- White: `.../2026-10-02-u10-1-t8-rerun/window/boards/u101-t8-A1-r2-20261002T052621/5cd/runner/lit-original/20261002T133745-0de824c1/5cd1e3dd00000000000000000923012c/wikipedia/{t20.jpeg,hilog.txt,maps-t5-16137.txt}`
- Lit (no T8): `.../2026-10-02-u10-1-bundle/window/boards/u101-20261002T014239/5cd/runner/original/20261002T015250-3a49eae2/5cd1e3dd00000000000000000923012c/wikipedia/{t20.jpeg,hilog.txt}`
- APK: `$HOME/a2hlab/app-inputs/wikipedia/wikipedia.apk` (sha256 eba82a0f).
