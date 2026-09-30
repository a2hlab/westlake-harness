# U6 prospective forecast: T7c + J7b + merged inputs

## What was wrong and what is now frozen

U5's missed native consumers and input failures cannot be erased by declaring a newer JAR/image. This forecast names the **actual repaired APIs**, preserves untouched native walls, and separates **first blocker**, **operation crossing**, and **t20 own UI**. It uses U5 and labeled T7c-only/J7b-only component pretests, **not results of a combined U6 sweep**.

Version **u6-t7c-j7b-v1** binds U5 native generation `7bc02de7`, **T7c's 27 image files plus stubs `366acc27`**, J7b **`381110a675fb543b6ad4102c8fc721fcb5673bc0da8644ececd1bab1ca60bec8`**, and 66 exact input inventories. **T7d has no artifact in this freeze.** Substituting T7d, N5/N6, another JAR, or repaired/re-signed inputs requires a new version before running; this is not a floating “latest U6” prediction.

The table contains **66 keys**: 22 preserve-own-UI forecasts, 17 retained-wall forecasts, 16 expected crossings, 9 uncertain/flaky cases, and **2 still input-blocked**. Expected crossing is not expected lighting: only catima and opencamera additionally predict own UI; 22 controls predict preservation. Four cohort keys are registered flaky (antennapod, fd-noice, fd-notes, fd-uhabits), so no deterministic single-attempt UI claim is made for them.

- `PREDICTIONS.csv`, `.json`, `.md`: per-key first wall or expected crossing, repair IDs, signatures, exact APK SHA, and log/t20 criteria.
- `FREEZE.json`: UTC freeze time, CSV SHA256, every executable prediction dependency and evidence file hash. Old CSVs `bae8fd74` and `97014f71` remain unchanged.
- `expected-run.json`: expected **119 runtime paths, 36 boot/image paths, and 66 APK + sidecar maps**, not merely top-level package names. Native libraries remain U5; only the runtime JAR and T7c boot set differ.
- `candidate.json`, `input-facts.json`, `apps-u6.json`: candidate facts and input plan. `apps-u6.json` is **not an installation receipt**; merged keys require a new staged input root with exactly the pinned APK/native set. The collector's temporary normalized directories do not authorize deployment.

## Per-component repair inventory

`api-repairs.json` contains five T7c API groups, six J7b service/API groups, and three input operations. Actual JAR member inventories are in `evidence/jar-api-members.json`; pinned source lines are in `evidence/j7b-source.json`.

| Artifact | Added/repaired API contract | Explicit limits |
|---|---|---|
| T7c stubs + image | TagSoup `Parser.setProperty/getProperty` and four property names | Not a full HTML parser; no general `parse/setContentHandler/setFeature` implementation |
| T7c stubs + image | `NetworkRequest.getNetworkSpecifier` | Does not repair CoroutineStart/class-loader behavior |
| T7c stubs + image | `MediaStore.Images.Media.EXTERNAL_CONTENT_URI/INTERNAL_CONTENT_URI` | `canManageMedia`, `Files.getContentUri` remain absent |
| T7c stubs + image | `NetworkInfo.getState` | No `ColorMatrix.setSaturation` repair |
| T7c stubs + image | `NetworkCapabilities.getLinkUpstreamBandwidthKbps/getLinkDownstreamBandwidthKbps` | `getSignalStrength` remains absent |
| J7b | AppWidget manager/class mapping + type-zero IAppWidgetService | Empty arrays, not real widget hosting |
| J7b | SystemVibratorManager `mLock` before `getVibratorIds`/`hasVibrator` | No physical vibration or EGL proof |
| J7b | Non-null WifiManager when IWifiManager is absent | Does not implement the missing service |
| J7b | Only ACTION_BATTERY_CHANGED sticky Intent fallback, level/scale/status/plugged | Defaults, not a hardware battery read; other actions unchanged; Camera JNI untouched |
| J7b | SearchManager's local ISearchManager in `sCache` | Not a real search backend |
| J7b | WallpaperManager `sGlobals` with type-zero wallpaper service | Null colors, not real wallpaper support |
| Inputs | Five signed merged APKs, sidecar cleanup, Subway's merged pin | No native provider fix, signature compatibility or successful install implied |

The J7b build receipt compares against **B5**, not J6. Six selected source hashes match its receipt; OnlineConnectivityManager is not listed there and is instead backed by pinned git source, compiled class inventory and the executed battery marker in the component pretest. No missing receipt is invented. Actual J6/J7b JAR SHA and member inventories are kept separately.

## Five new inputs rescanned

All DEX and relevant ELF members of the **signed merged APKs** were rescanned, not copied from the base-only risk labels. Native inventories are **34/18/10/20/33** for burgerking/firefox/mcdonalds/subwaysurfers/x. All 65 DEX members in those five APKs have the same hashes as the original base DEX members; merging repairs input completeness, not Java code. Thus native mozglue/Realm requirements survive. All five have one selected APK and no split/pin blocker in the normalized target input plan.

The 59 unchanged keys have their old APK and sidecar bytes revalidated; the remaining two keys, fd-seal/toutiao, are rescanned against the claimed repaired VM input root. No source inputs, APKs or runtime artifacts are modified or committed.

### Two repairs are not physically complete

Independent read at 02:58 found fd-seal metadata lists 6 libraries but the directory contains 9: `libaria2c.zip.so`, `libffmpeg.zip.so`, `libpython.zip.so` remain. Toutiao metadata lists 137 but its directory has 138, including 32-bit `libcvt.so`. The batch checks inventory equality **before** ELF headers, so its actual first refusal is `native sidecar inventory differs from app-input`.

Evidence: `evidence/input-repair-gap.json`, final `input-facts.json`. The outer loop explicitly instructed this forecast to retain both as **input not repaired**; oc-t4 will later move originals to quarantine and run resolve. Those future inputs **must not** be scored under this frozen inventory. The intended runtime next wall for both remains unknown after a genuine input crossing. Subway's merged APK pin is `4b06bd74`, not the intermediate base `ffd32287` or obsolete `5904cda2`.

## Important per-key distinctions

- **fd-reader**: J7b passes vibrator/wallpaper then reaches TagSoup; T7c supplies `setProperty`. Predict the combined crossings, but not an invented next fatal or a full HTML success.
- **fd-app / Shattered Pixel Dungeon**: predict past the vibrator lock; U5 masked EGL, so the next EGL/GL result is unknown rather than a recycled fid-null claim.
- **fd-wifianalyzer**: J7b's actual next exception is `CountryPreference.<init> -> wb0.H -> Object.getClass` null (original lines 27186–27188), **not established evidence of a missing WifiManager method**.
- **wikipedia / gallery / plus / x**: T7c-only pretests and actual missing members support SSLSockets / next MediaStore APIs / ColorMatrix / signal-strength next-wall forecasts. T7d's proposed fixes are excluded.
- **feeder / LibreTube**: a CoroutineStart error or a disappeared process alone is not proof of the first fatal. Feeder's next-wall hypothesis is conditional on causal review; LibreTube's next fatal stays unknown.
- **Immich / Jitsi / VLC**: distinguish provider or retryable loader precursors from later process-ending errors. The table retains the ordered candidates and requires first-blocker review, not the nearest warning before a crash.

## Freeze, identity and later scoring

```sh
python3 benchmark/2026-10-01-u6-prospective/forecast.py --verify
python3 benchmark/2026-10-01-u6-prospective/test_forecast.py
python3 benchmark/2026-10-01-u6-prospective/forecast.py --check-run actual-run-bindings.json
```

Before freezing, `--write` regenerates outputs and `--freeze` records hashes. Both collection and generation refuse overwrite after freezing. `actual-run-bindings.json` must be produced from actual post-deployment/batch identity, with the same schema as `expected-run.json`; copying the expected file is not verification. These checks do not replace G1/G2/G3/native deployment gates.

For every scheduled first attempt, bind APK, native sidecars, runtime/image inventories, package/PID and screenshot. Classify **first causal blocker**, **positive crossings of named operations**, and **t20 screenshot** separately. Missing errors, earlier masking or missing identity remain unknown; matching class strings/registration inventories are not positive execution. The pure `score_reviewed` helper implements these distinctions and has positive, failed-promise, wrong-identity, masking and flaky controls. Do not substitute later retries for the first attempt, or attribute a combined change to one repair.

Validation and landing receipts are in `validation/` and `HANDOFF.md`. This task is entirely offline; a frozen forecast is neither an executed sweep nor permission to deploy an incomplete candidate.
