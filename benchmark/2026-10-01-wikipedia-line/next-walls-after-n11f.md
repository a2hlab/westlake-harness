# Wikipedia — predicted walls after N11f (single-copy bridge/runtime)

Prediction table built from the **old-route** Wikipedia wall chain (DIGEST) + the **U8/U9 Wikipedia run evidence**. Each
row: the wall, the evidence path, the predicted fix + verified source, and whether it is already handled in U9 (so you
know which are real *next* walls vs already-cleared). **Predictions — to be confirmed on the first N11f window, read by
hilog/screenshot.**

## Headline: N11f very likely dissolves Wikipedia's *current* dominant wall (the `sessions_` miss)

The U8-vs-U7 analysis (`benchmark/2026-10-01-wikipedia-line/u8-vs-u7-lit-analysis/README.md`) pinned why Wikipedia is a
coin-flip today: it creates two self-drawing surfaces — `org.wikipedia.DefaultIcon` (launcher alias, no UI) and
`org.wikipedia.onboarding.InitialOnboardingActivity` (the content). On the render-thread re-query **after
`resolve_oh_wm_funcs` fresh-dlopen**, BOTH return `unknown sessionId` (the `sessions_` registry miss); only the
**last-stamped** session is rescued by `OH_GfxShim BBQ.update`. Wikipedia lights iff the *content* is stamped last
(U8 lucky → lit; U7 content-first → white). The analysis's own recommended root fix: "don't rely on last-session rescue;
make `getOhNativeWindow` resolve the re-queried session from a **single shared `sessions_` registry** so BOTH sessions
keep their window."

**`sessions_` lives in `liboh_adapter_bridge.so`** — `oh_window_manager_client.cpp` (defines `sessions_`, e.g.
`:1921 sessions_[persistentId]=entry`, `:938 sessions_.find`) and `oh_anativewindow_shim.cpp` are both in
`native/bridge-sources.json`. The "fresh-dlopen second copy" whose `sessions_` is empty **is the second bridge copy**.
N11f makes the bridge single-copy → **one shared `sessions_` registry** → the render-thread re-query finds each session's
own `OHNativeWindow` → no last-session lottery → Wikipedia should light **deterministically**, content surface drawn.
So N11f is not just a correctness cleanup for Wikipedia; it is plausibly *the* fix for its headline wall. **Confirm on the
window:** maps show single bridge, and the hilog shows `BBQ.getSurface: returning Surface … (sessionId=InitialOnboarding)`
(not "empty Surface"). If it still white-screens with single-copy maps, the `sessions_` miss had a second cause (the
fresh-dlopen re-resolves funcs from a path outside the two owners) → chase `resolve_oh_wm_funcs`.

## Prediction table (walls Wikipedia hits *after* the content surface renders)

| # | Predicted wall | Evidence path | Predicted fix + verified source | U9 status |
|---|---|---|---|---|
| 0 | **`sessions_` registry miss → white unless content stamped last** (the current dominant wall) | `2026-10-01-wikipedia-line/u8-vs-u7-lit-analysis/README.md`; U8-lit hilog `westlake-harness-t4/…/2026-10-01-u8-sweep/5ea-seq-v1/…/wikipedia/hilog.txt`; U7-white `westlake-harness-wiki/benchmark/2026-10-01-u7-sweep/61b/…/wikipedia/hilog.txt` | **N11f itself** (single bridge ⇒ single `sessions_`). Source: this patch + `n11-single-owner` oracle `c2508ebdd`. | **Dissolved by N11f** (confirm) |
| 1 | **connectivity reports offline → `MainActivity.onGoOffline` → `MainFragment.getCurrentFragment()` NPE → System.exit(1)** | `2026-09-29-wikipedia-line/README.md` R1 + `results.json` rounds[0]; `r2-investigation.md` | `ConnectivityManagerAdapter` backed by the OH default network (`core/java/ConnectivityManagerAdapter.java`, `getActiveNetwork`/`registerDefaultNetworkCallback` real); the old `mls-online.jar` (SHA `83c5ef21`) stubs are the fallback. Source: DIGEST §381 (connectivity "都这样修掉"). | **Likely already in U9** (ConnectivityManagerAdapter is in the current tree) — confirm it returns online, else onGoOffline fires |
| 2 | **`android.text.Layout: width -79` assertion → StaticLayout build → main-thread `exit(1)`** (visible window width collapses to ~1px) | DIGEST B.12 + hollow48 `benchmark/2026-09-26-operator-layout79fix-48/` | `WindowSessionAdapter.relayout` width/height **clamp** (CLAMP48 smali: cache last-good, fall back to `getMaxBounds()` when ≤1). Source: hollow48 `adapter-runtime-bcp.CLAMP48.jar` (inner dex `c5bd7fd2`). | **Confirm in U9** (BCP jar patch — may or may not be in the unified boot image) |
| 3 | **Compose/HWUI render: PNG decode (skia `inflate`) on the main thread → SIGSEGV on the 128 KiB child stack guard page** | DIGEST §383 (Wikipedia Compose recomposition PNG decode); §389 (Compose-system apps survive-but-white) | Remove the fork-added `---p` guard page below `[stack]` / enlarge the child main-thread stack (my worktree `build_v5_bigstack.py`, `build_v7_looperguard.py`). Source: `2026-09-29-wikipedia-line/` v5/v7. | **Open** (stackfix attempts drafted, not confirmed landed in U9) |
| 4 | **No network: `android_getaddrinfo` → EPERM** (article fetch fails; onboarding first-screen may not need net) | DIGEST §382, §384 | Map Android `INTERNET` → OH `ohos.permission.INTERNET` at install (BMS-installed `reqPermissions` is empty; gid 3003 alone is insufficient — §384 proved). Source: §382/§384. | **Open** (install-time permission mapping) |

## Already-cleared on the way here (confirm each is in the unified U9, not a regression)
These were walls on the old route *before* the ones above; Wikipedia must pass them again on U9:
- **Theme attribute `ID=2130969834` / `Theme.AppCompat`** — cleared by the activity-level theme JAR (DIGEST §318/§354, 2026-09-29 R1 "theme 0x7f130026 resolves").
- **B6 `Activity.attach → getTheme → getApplicationInfo` SIGSEGV** — cleared by the ART `libsigchain` fix (DIGEST §325, cx-t0 `6cb40cd6`); ART handles the implicit null-check SIGSEGV and returns past `getTheme`.
- **`Html.fromHtml` / `org.ccil.cowan.tagsoup.Parser` NoSuchMethodError** — cleared by T7d (adapter-mainline-stubs + full AOSP tagsoup, jar `d8b2406e`, DIGEST §389).
- **BMS entry: launcher alias `org.wikipedia.DefaultIcon` ClassNotFound** — cleared by `ActivityInfo.targetActivity` from manifest (DIGEST §354, `alias-entry/`); and the 10 sandbox roots uid/mode/chcon (§350/§352, `sandbox-prep/`).

## Reading order on the N11f window (how to classify the stop)
1. Maps single-copy (bridge=1)? If no → N11f didn't take; stop. If yes → `sessions_` shared, expect content surface drawn.
2. hilog `BBQ.getSurface … (sessionId=InitialOnboarding)` **non-empty** → wall 0 dissolved. Empty → chase `resolve_oh_wm_funcs`.
3. `onGoOffline`/`getCurrentFragment` NPE present → wall 1 (connectivity still offline).
4. `Layout: … -79` present → wall 2 (width clamp missing).
5. `SIGSEGV` with fault addr in `[stack]`-adjacent `---p` during skia `inflate`/Compose → wall 3 (stack guard).
6. `android_getaddrinfo … EPERM` → wall 4 (no INTERNET perm) — expected on any real network call regardless.

Each wall above an earlier-cleared one is only reachable once the earlier ones hold on U9; a regression in the
"already-cleared" set would surface *before* these. Screenshots are ground truth — `alive`/white ≠ `lit`.

Evidence index: DIGEST `.octos/KNOWLEDGE-DIGEST.md` §318/§325/§350/§352/§354/§381/§382/§383/§384/§389, B.12;
`2026-09-29-wikipedia-line/` (README, results.json, r2-investigation.md, CONNECTIVITY-BOOT-IMAGE-HANDOFF.md,
build_v5_bigstack.py); `2026-10-01-wikipedia-line/u8-vs-u7-lit-analysis/README.md`; `sessions_` owner
`vm-copies/westlake-current/framework/window/jni/oh_window_manager_client.cpp` ∈ `native/bridge-sources.json`.
