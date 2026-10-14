# T7d baseline — the first wall each target hits under U6 (=T7c), for the board wall-shift verdict

Source: cc-wiki T7c package-deploy board run on 61b (`benchmark/2026-09-30-dex2oat-l2/runs/t6-61b…-20261001T021447/batch/t6/61b…/<app>/hilog.txt`), which is U6 (=T7c: tagsoup + the 4 boot-api stubs) for these apps. **To be reconciled against the U6 full-sweep hilog when it lands** (outer ring ACK(80) 03:39); the first-fatal API is expected identical (same jar).

T7d success criterion per app = **the target API error below is GONE** from the post-T7d hilog (wall passed). Whether the app then lights depends on the *next* wall (noted where already visible). This is the FZ-005 `wall_passed` evidence model: "that API's failure gone, first fatal moved elsewhere" — do NOT read "passed the wall but still not lit" as a T7d failure.

| app | T7d target first wall (under T7c) | severity | log evidence | T7d fix | likely NEXT wall after T7d |
|---|---|---|---|---|---|
| **wikipedia** | `NoClassDefFoundError: Failed resolution of: Landroid/net/ssl/SSLSockets;` (OkHttp Dispatcher; background thread, process kept alive) | FATAL to network | hilog.txt:58965 (02:16:36) | `SSLSockets` new class (isSupportedSocket→false) → OkHttp falls back to standard TLS | none obvious — network should work; watch for a real page render |
| **fd-gallery** | `NoSuchMethodError canManageMedia(Landroid/content/Context;)Z` in MediaStore (**J_invokeStaticMain_main_threw** — main dies) + earlier worker `getContentUri(String)Uri` in MediaStore$Files | FATAL (main) | hilog.txt:56643 (canManageMedia, main) + :56160 (getContentUri, Thread-4) | both added (canManageMedia→false, getContentUri→content://media/<vol>/file) | none obvious — both walls fixed; watch for an OH media-provider query wall |
| **fd-plus** (osmand) | `NoSuchMethodError setSaturation(F)V` in ColorMatrix (Caused by, crash stack) | FATAL | hilog.txt:56780 (02:21:50) | ColorMatrix.setSaturation added (no-op) | **`NullPointerException MapInfoLayer.isMapControlsVisible() on null` (J_invokeStaticMain_main_threw, hilog.txt:66134)** — may be independent app-logic/init wall; T7d may pass the ColorMatrix wall but NOT light fd-plus |
| **x** (twitter) | `NoSuchMethodError getSignalStrength()I` in NetworkCapabilities (Caused by, crash stack) | FATAL | hilog.txt:40474 (02:23:41) | NetworkCapabilities.getSignalStrength added (→MIN_VALUE) | **`IllegalStateException: The application object graph is not defined … ApplicationObjectGraphProvider` (main threw, hilog.txt:44730)** — Twitter DI framework wall, independent; T7d passes getSignalStrength but x likely hits this next |

## Expected T7d board outcome (honest)
- **wikipedia, fd-gallery**: target walls are the app's blocking API misses → T7d likely lets them progress (possibly to own-UI). Best T7d "lit" candidates.
- **fd-plus, x**: T7d passes the ColorMatrix / getSignalStrength walls, but each has a *further, non-API* wall already visible in the T7c hilog (osmand MapInfoLayer NPE; Twitter object-graph DI). Expect **wall_passed** (API error gone) rather than **t20_lit**. That still counts as T7d progress + is valid FZ-005 evidence.
- **fd-libretube, fd-feeder** (not T7d targets): no android/java member wall — untouched by T7d.

## Board verdict rule (T7d on 61b, after U6)
For each of the 4 targets, read the post-T7d hilog:
1. **PASS-wall** iff the target API error above is ABSENT.
2. **lit** iff its t20 screenshot shows own-UI (ground truth).
Report per app: {api_error_gone: yes/no, new_first_fatal: <line>, t20_lit: yes/no}. Controls HW/ZZ/aegis/ooniprobe must stay lit (no regression).

## Board list addendum (ACK(80) mid-turn 03:45+)
- **noice, fd-noice** added (SSLSockets beneficiaries, per cx-bms: blank-screen caught the SSLSockets CNF).
  Same wall as wikipedia (row 1). **fd-noice is a flaky-registered key → 3× under T7d AND 3× for the U6
  baseline** before a verdict; others 1×. T7d SSLSockets is expected to clear their CNF.
- **fd-libretube**: NOT an SSLSockets app (0 hits). Its wall is `IncompatibleClassChangeError: tagsoup
  Parser does not implement XMLReader` (see ANOTHER-TRACK-FINDINGS.md) — a tagsoup-stub defect, NOT fixed by
  T7d. Do not expect T7d to light libretube.
- **fd-feeder**: wall is `SystemVibratorManager.getVibratorIds` NPE (null vibrator service) — NOT fixed by T7d.
