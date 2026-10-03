# U16 wall clusters: the 30 non-lit keys of U13 stage A fall into 19 clusters. U14 owns 13 keys (11 predicted first-fatal moves), U15 owns 7 (4 moves); the only unowned cluster with a predicted move is the empty WifiManager stub (1 key)

#90, offline. Nothing ran on a board.

## Data

**Input.** The 219 U13 stage-A runner records bound by the outer decision
(`2026-10-03-u13-stage-a-decision/selftest-u13-stage-a.json`). That is 159 distinct keys plus the activation-smoke
controls helloworld / zigzag / probe, which are excluded.

**"Non-lit".** A key with **no lit run in any of the four window sign-offs**
(`2026-10-03-u13-stage-a-plan/window{1..4}-signoff/outer-signoff.json`). This gives **30 keys, 32 runs**
(`population.json`, `per-run.json`).

**What was wrong in the first count.** Windows 1–3 record `runs` / `lit_runs` / `verdicts` per key, but window 4
records a single `verdict`. Reading only the first schema made 16 window-4-lit keys look non-lit (46 instead of 30).
`collect.py` reads both.

**Signatures** (`collect.py`). They are imported, not copied, from `2026-10-03-u13-first-fatal-clusters/collect.py`,
which imports `2026-10-03-u12-predicted-vs-actual/compare.py`:
- the terminal is `first_fatal.py` + `cluster_first_cause.cluster_key`;
- the wall is the earliest WALL line before the terminal, or the innermost `Caused by:` under
  `ensureBindApplication FAILED`;
- bind is per `bind_status.py`;
- near-fatal libraries come from `dlopen_failures.scan --near-fatal 3`.

**Clustering** (`clusters.py`). Keys are grouped by first fatal. When the terminal is only a consequence (process
disappeared, bind failed, `J_invokeStaticMain` wrapper), the wall decides instead. Alive keys without a fatal are grouped
by their window mechanism (`2026-10-03-white-residual-u13`). Every assignment names a signature that the script asserts
is present in that key's own row, so the table cannot drift from the data.

## The table (`clusters.csv`, sorted by keys; `per-key.csv` has one row per key with its run path)

| # | cluster | keys | owner | predicted first-fatal moves | picture / confidence |
|---|---|---|---|---|---|
| A | Flutter raster SIGSEGV (`1.raster`): libflutter's `eglCreateWindowSurface` binds platform libEGL with the AdapterAnw wrapper | **4**: localsend, fd-kitchenowl, fd-fluffychat, fd-libre | **U14** `u14-flutter-libandroid` fff9be31 (carried by U15 9b824502) | **4** (high) | next wall unknown |
| B | M2 full-screen WebView (typed zero provider), alive white/black, no fatal | **4**: randomlydie, yatoo, jiten-webview, webrtc-check (black) | **none**. Route a in `m2-webview-roadmap`; A0 window 2 pending | 0 (alive) | own content only with a real WebView (route a: 2 after A1, 4 after A2) |
| C | bionic `_ctype_` (Realm) in the native domain, bind fails | **2**: mcdonalds, fd-im-vector-app | **U14** `u14-native-abi-v2` f8619ad5 | **2** (high) | |
| D | bionic LIBC in the native domain: Gecko `__gnu_strerror_r`, VLC `__pthread_cleanup_push` | **2**: fd-fennec_fdroid, vlc | **U14** `u14-native-abi-gecko` 7605812c | **2** (fennec high, vlc medium) | |
| E | `can't create bitmap without a color space` | **2**: privacybrowser, fd-musicplayer | **U15** `u15-framework-bitmap` (framework 9e55e286, in the U15 bake) | **2** (high) | |
| F | M3 GLSurfaceView EGL IAE, alive white | **2**: fd-app (Unciv), shatteredpixeldungeon | **U15** `u15-runtime-m3` 94c31177 | 0 (alive) | IAE gone (medium) |
| G | dropped close / dialog under the Activity window (bridge), alive white | **2**: dddmodel2, fd-AppManager | **U14** `u14-bridge-m5-m6` 7daa5435 (dddmodel2 needs U13's M1) | 0 (alive) | own dialog (med) / own splash (med-low) |
| H | termux finishes itself (bind before onStart) | 1: termux | **U14** `u14-jar-v1` 0349eb83 | 1 (high): moves to TermuxInstaller's bootstrap check | own error dialog |
| I | toutiao: app-ns `libicui18n.so` ENOENT, then SIGSEGV on the same thread 1 ms later | 1: toutiao | **U14** `u14-appns-public-libs` 341c1260 + ICU | 1 (medium) | |
| J | `android.bluetooth.le.ScanCallback` at bind | 1: fd-plus | **U14** `bt-le-scancallback` stubs 87cf65cc | 1 (high) | |
| K | immich bind `VerifyError A2.b` (android.net.nsd), then libcronet `ATrace_beginSection` | 1: fd-immich | **U15** `u15-stubs-nsd` 94a94905 + `u15-flutter-libandroid-v2` 9b824502 | 1 (medium) | then the A path |
| L | AppCompat theme: the alias gets the application theme | 1: fd-api | **U15** `u15-jar-v1` 20e748e5 | 1 (high) | |
| M | x: trampoline → second process, white by timing | 1: x | **U15** `u15-jar-v1` 20e748e5 | 0 (alive) | lit medium |
| **N** | **`android.net.wifi.WifiManager` is an empty boot stub**: NoSuchMethodError `isScanThrottleEnabled()` at main | 1: fd-wifianalyzer | **none → U16** | **1** (high, if all 8 invoked methods are added) | its own "no networks / Wi-Fi off" UI (medium) |
| O | window session not connected to SceneSessionManager → `InvalidDisplayException` | 1: chessclock | none (mechanism known, no fix designed; chessclock only in U13) | 0 | |
| P | `GetLongField` JniAbort inside the app's own JNI `getSceneInfo` (null object) | 1: glmark2 | none (cc-wiki: on hold) | 0 | |
| Q | app `lateinit weatherView` (the earlier `CoroutineStart` CNFE is our own non-fatal prime) | 1: fd-breezyweather | none (undiagnosed) | 0 | |
| R | alive white, mechanism unclassified | 1: fd-saber | none | 0 | |
| S | never launched: desktop tile not found (lit via `aa start`) | 1: frequent-habits | none (launcher, not a runtime wall) | 0 | |

**Totals.**

| owner | keys | predicted first-fatal moves | alive keys whose t20 picture is predicted to change |
|---|---|---|---|
| U14 | 13 (A, C, D, G, H, I, J) | **11** | 2 (G) |
| U15 | 7 (E, F, K, L, M) | **4** | 3 (F, M) |
| none | 10 (B, N, O, P, Q, R, S) | **1** (N) | 4 (B, only with route a) |

## U16 candidates (unowned, predicted move > 0)

**One cluster: N, the WifiManager boot stub** (`evidence/wifimanager-gap.txt`).
- **The gap.** fd-wifianalyzer's DEX invokes 8 `WifiManager` methods: `getConnectionInfo`, `getScanResults`,
  `is5GHzBandSupported`, `is6GHzBandSupported`, `isScanThrottleEnabled`, `isWifiEnabled`, `setWifiEnabled`,
  `startScan`. The class in adapter-mainline-stubs is **empty**: constructor only, in U15 94a94905 and in U14 87cf65cc.
  The board fails on the first method reached.
- **The minimal fix.** Same shape as `bt-le-scancallback` / `u15-stubs-nsd`:
  - the stub carries those 8 public members with the AOSP 14 signatures and **"device without Wi-Fi" answers**
    (`isWifiEnabled` false, empty scan list, `startScan` false, `setWifiEnabled` false, a default `WifiInfo`);
  - it is a BCP change, so it needs the FZ-005 bake and goes into the U16 stubs batch.
- **Prediction:** first fatal moves for 1 key (high). The t20 picture is its own no-Wi-Fi UI (medium).
- **Not to do:** adding only `isScanThrottleEnabled`. It would just move the NSME to the next method.

**Unowned with prediction 0 (not U16 candidates; each needs diagnosis first):**
- O chessclock;
- P glmark2;
- Q breezyweather;
- R fd-saber;
- S frequent-habits (a launcher miss, not a runtime wall).

**B (M2, 4 keys) is the largest unowned cluster.** It has no first fatal, so it is not ranked by this rule. Its route is
already chosen (route a); its gate is the A0 probe, window 2 approved and pending.

## Second walls already visible behind owned clusters (watch, not predictions)

| key | after its owned fix |
|---|---|
| fd-libre (A) | `libmpv.so` needs `libmediandk.so`, refused with `Xpm check failed for libmediandk.so, errno for mmap is: 22` (OH code-signature check), caught. Only libre among U13 hilogs. |
| x (M) | `libcrashlytics.so` `__register_atfork` not found (caught). Normal-domain bionic gap, same family as fd-meet (`u15-compat-v3`, not built: 0 predicted). |
| fd-app (F) | background `MediaStore.scanFile` NSME (kept alive) |
| fd-musicplayer (E) | background `MediaStore$Audio$Artists` NCDFE (kept alive) |
| toutiao (I) | background `MediaStore$Downloads` NCDFE (kept alive) |
| fd-musicplayer, fd-im-vector-app, fd-fennec_fdroid | their alias splash theme changes under U15 (`u15-alias-theme-watch`), visible only once the fatal walls above move |

**The `MediaStore` background NCDFE / NSME** appears in three keys, all non-fatal today. It is the next candidate only if
one of them becomes fatal after its owned fix.

## Top 5 by keys blocked

1. A Flutter EGL, 4 (U14);
2. B M2 WebView, 4 (unowned, route a / A0);
3. C `_ctype_`, 2 (U14);
4. D Gecko/VLC LIBC, 2 (U14);
5. E Bitmap ColorSpace, 2 (U15).

F (M3, U15) and G (bridge, U14) also block 2 keys each.

## Rules this round sets

- **Read every sign-off schema before counting.** Window 4's single `verdict` field made 16 lit keys look non-lit
  (46 vs 30).
- **A missing-method NSME on a stub class means auditing the whole class against the app's calls**, not adding one
  method. WifiManager is an empty class, so the fix size is the app's call set (8).

## Files

- `collect.py` → `population.json`, `per-run.json`.
- `clusters.py` → `clusters.csv`, `per-key.csv`.
- `evidence/collect.log`, `evidence/wifimanager-gap.txt`.
- `results.json`.
