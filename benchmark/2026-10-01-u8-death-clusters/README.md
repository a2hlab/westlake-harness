# U8 non-lit death clusters (66 keys, offline)

Dispatch (board ACK(90) 14:38:37): cluster the U8 non-lit keys by innermost Caused-by + first frame (native crashes use the faultlog stack's first non-system frame). Boards untouched. Method: `first_fatal.py` (0944217a4) + `cluster_first_cause.py` (innermost cause, wrapper RuntimeException never a key).

## Total

U8 signed 166 keys: **99 lit, 67 non-lit** (dead 53, alive-white-window 8, alive-launcher-foreground 3, alive-black-window 1, app_failed 3). The 67 non-lit keys are clustered below.

## Clusters (sorted by keys blocked, descending)

| Cluster | Keys | Coverage | Notes |
|---|---|---|---|
| **other** | 37 | not covered by N10b/J10b/N11 | Various distinct first-causes (NullPointerException, UnsatisfiedLinkError, ClassNotFoundException, signal crashes, system-exit). See clusters.json for per-key cause + first frame. |
| **n11-double-load-white-window** | 12 | **N11** (two bridge/runtime copies → unknown sessionId → white window) | fd-AppManager/fd-app/fd-noice/termux/fd-mobile (alive-white-window), fd-shatteredpixeldungeon/fd-uhabits/cv2-org-andresoviedo-dddmodel2 (alive-white-window), cv2-anupam-acrylic (alive-launcher-foreground), x (alive-black-window). Mechanism from double-load analysis: createSession goes to runtime CL bridge, getOhNativeWindow goes to default-namespace bridge → unknown sessionId → empty Surface → white. |
| **j10b-appcompat-actionbar** | 6 | **J10b** (appcompat action-bar ISE) | cv2-com-codedead-advancedpassgen/codedead-deadhash/deva-knot/emmanuelmess-itsdicey/maxistar-textpad (dead), cv2-org-secuso-privacyfriendlymemory/privacyfriendlyyahtzeedicer (alive-launcher-foreground). All `IllegalStateException: This Activity already has an action bar supplied by the window decor` at `AppCompatDelegateImpl.setSupportActionBar`. |
| **getactivityinfo-namenotfound** | 4 | not covered | cv2-com-aptasystems-dicewarepasswordgenerator/tomato timerdroid/woefe-shoppinglist/ruesga-android-wallpapers-photophase. `ApplicationPackageManager.getActivityInfo(:570)` throws `NameNotFoundException` for the app's own Activity. |
| **no-termination** | 3 | not covered | cv2-com-bytehamster-flowitgame (dead, no-observed-termination), fd-fennec_fdroid/firefox (dead, process-disappeared-cause-unknown). No first-fatal found in hilog. |
| **app_failed-input** | 3 | not covered (input gate) | cv2-com-page-bizzle/trianguloy-clipboardeditor/frequent-habits (app_failed). Input resolution failure before install; no hilog. |
| **n10b-flutter-libandroid** | 2 | **N10b** (Flutter private preload libandroid.so) | fd-kitchenowl/localsend (dead). `UnsatisfiedLinkError: Flutter private preload libandroid.so: Error loading shared library` at `Runtime.load0`. |

## Coverage by in-flight fixes

- **N10b** covers: n10b-flutter-libandroid (2 keys). The `n10b-emboss-asset` cluster (Typeface VM / NDK AssetManager / Emboss) is **empty** in U8 — those walls were already passed in U7/U8 or are not present in this cohort.
- **J10b** covers: j10b-appcompat-actionbar (6 keys).
- **N11** covers: n11-double-load-white-window (12 keys) — the double-load root cause (two bridge/runtime copies → unknown sessionId → white window), per double-load analysis in `whitewin-diff/double-load/`.
- **Not covered**: other (37 keys), getactivityinfo-namenotfound (4), no-termination (3), app_failed-input (3).

## Evidence

- Per-key first_fatal results: `/tmp/u8-death-results.json` (copied to `clusters.json` evidence).
- Run dirs: `westlake-harness-t4/benchmark/2026-10-01-u8-sweep/{5ea,61b}-seq-{v1,cv2}/`.
- outer-signoff: `benchmark/2026-10-01-u8-sweep/outer-signoff.json` (master).
- double-load mechanism: `benchmark/2026-10-01-u8-flaky-repeat/whitewin-diff/double-load/REPORT.md`.
