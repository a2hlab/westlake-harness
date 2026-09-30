# r17s 3b523289 audit on 61b — PASSED (2026-09-30)

**One line:** the outer-loop audit of r17s `3b523289` (the unified JAR cc-wiki holds on 5ea) on 61b:
**all 9 must-not-regress apps lit, TLS wiring active with no regression, and r17s beats r17p** (markor,
dead on r17p, is lit under r17s). fd-meet/dlopen-four stay dead (native / app-internal, unchanged). JAR SHA
untouched; 61b restored to r17p and released.

## Result (`--reinstall`, 14 keys + HW control)

| group | keys | verdict |
|---|---|---|
| must-not-regress (9) | fd-etar, markor, antennapod, fd-com-amaze-filemanager, fd-tusky, fd-k9, fd-android, aegis, fd-auxio | **all yes/yes** — no regression |
| RestrictionsManager | fd-meet | no/no — fetcher built, advances past its NPE, hits null-`Collection.iterator` (honest progress) |
| dlopen (native) | fd-app, fd-client, fd-im-vector-app, mindustry | no/no — deps unreachable from the app namespace (cx-t0) |
| HW control | helloworld | yes/yes (child_hilog 5877) |

`TOTAL alive_t5=9 alive_t20=9` (of the 14). Screenshots (FLAW-007): tusky login page, markor doc browser,
antennapod welcome, **fd-k9 "updating database" screen** — all render their own UI under r17s.

## The three fixes, on this board

- **(a) TLS wiring — active, no regression.** Every bind logs `[B8-TLS] SSLContext.TLS -> Westlake (direct
  newInstance) + setDefault; okhttp beats TlsShimProvider`. The 9 lit apps (incl. TLS-heavy tusky/k9) prove
  the provider swap breaks nothing. (Real handshake needs a reachable HTTPS endpoint — separate, cc-wiki/5ea.)
- **(b) RestrictionsManager — fetcher works** (`[B8-FETCH] restrictions RestrictionsManager built`); fd-meet
  not lit (null-Collection wall behind it).
- **(c) dlopen app-path probe — no-op** (`[B8-DLEXP] app classloader unavailable (ctx=null); skipped`): the
  thread context classloader is null at `B7BindFixes.apply()` in the OH child, so the DexPathList append
  never ran. dlopen stays native.

## compare_runs vs r17p (by-hand — runs predate `runtime-fingerprint.txt`)

Same board 61b, same **boot_id 58aef9fc** (cx-t0's `installer-r17p-61b` A/B ran on the same boot — no
reboot), same `--reinstall` method → **exactly one variable: the JAR** (`3b523289` r17s vs `a0ed5c4f` r17p).

- **held lit** on both: aegis, antennapod, fd-android, fd-k9, fd-tusky.
- **r17s WIN:** `markor` — r17p A/B = `no/no` (child_hilog 0), r17s = `yes/yes`. The r17r addToDisplay
  power-flag fix (carried into r17s) lights markor that r17p could not.
- **unchanged dead:** fd-meet, fd-app/fd-client/fd-im-vector-app/mindustry.
- **Conclusion:** single variable (the JAR); r17s adds markor over r17p and regresses nothing → **r17s ≥
  r17p on 61b**. Cleared for the three-board unified sweep.

## Follow-up — the dlopen app-CL reflection experiment (deferred, not done here)

The outer loop asked for the "reflection get app-CL" dlopen experiment. It needs a **source change to (c) +
a rebuild = a different SHA**, so it can't ride the unified JAR (`3b523289`, which must stay identical
across the three boards). Run it on a **throwaway** JAR next round.
- **Hook:** `ActivityThread.currentActivityThread().mBoundApplication.info.getClassLoader()` (LoadedApk), not
  `Thread.currentThread().getContextClassLoader()` (null at `apply()`).
- **Prediction:** still native — OH's native-loader uses the namespace **frozen at classloader creation**,
  not `DexPathList.nativeLibraryPathElements` at load time, so appending dirs to the app CL's DexPathList
  likely won't let libgdx/libarc reach libstdc++/libOpenSLES. The experiment would confirm cx-t0 ownership.

## Files
- `results.json` — per-group verdicts, the by-hand single-variable compare, the follow-up hook + prediction.
- `runs/r17s-audit-61b/.../` — 14-key `--reinstall` batch (t5/t20 + facts + hilog).
- `runs-hw/hw-r17s/.../` — helloworld control. `deploy-receipt/` — deploy/rollback receipt.
