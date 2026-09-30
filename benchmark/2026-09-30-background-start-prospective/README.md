# Background-Activity permission: frozen prospective forecast

Previous call-name searches missed Wikipedia's `ActivityResultLauncher` bridge, while Splash class names alone overstated startup reachability. This forecast resolves explicit Intent targets, retains unresolved branches, and separates **next-Activity progress** from **a visible destination page**. It does not treat process survival as a page or a static callsite as a measured permission denial.

**66 keys; 65 matching base APKs; 6,603,394 DEX methods; 6,011 Activity-start callsites.** [v1 CSV](freezes/v1/predictions.csv), [detailed witnesses](freezes/v1/predictions.json), [freeze receipt](freezes/v1/freeze.json). No board operations were performed; no post-grant results were consumed **before either freeze**. After the explicit outer handoff, [v0 backtesting](backtests/v0-bglaunch-5ea/README.md) found calibration progress **4/5 (80%)**, pages **1/5 (20%)**, and one unseen abstention. The supplied records contain 14 captures and 4/7 apps alive at t5/t20 (5 app processes, helpers excluded).

## Freeze and predictions

Full v1 froze at **2026-09-30 02:57:04.755686 +08:00** and its SHA was announced on board item 91 immediately afterward:

```text
bf6931c9668e208513c02867d58b8f6a47c4913e303dc9fa85e4e0e51886f3a3  freezes/v1/predictions.csv
```

| Tier | Keys | Forecast |
| --- | ---: | --- |
| `screen_likely` | 6 | Disclosed calibration cases: progress and destination page expected |
| `advance_likely` | 13 | Explicit startup target; progress predicted, destination page unknown |
| `advance_possible` | 7 | Deep, input-dependent or merged-callback path; abstain |
| `candidate_unknown` | 25 | Startup/Splash call found, destination or reachability unresolved |
| `no_static_startup_hit` | 13 | No bounded witness; abstain, **not proof of no effect** |
| `no_permission_benefit_predicted` | 1 | Termux negative control: second Activity already scheduled; granting this permission alone is not expected to repair its first frame |
| `unknown` | 1 | Subway Surfers APK identity mismatch; not scanned |

The 13 non-calibration progress candidates are `fd-AppManager`, `fd-noice`, `markor`, `fd-android`, `fd-etar`, `fd-k9`, `fd-libretube`, `fd-minetest`, `fd-organicmaps`, `fd-shatteredpixeldungeon`, `fd-uhabits`, `toutiao`, and `noice`. These are falsifiable **incremental-benefit hypotheses**, not 13 established permission walls. Some may already dispatch successfully or stop before the identified call. In particular, a map placeholder or account page does not imply working map/network functionality.

Initial [v0](freezes/v0/freeze.json) remains unchanged: 02:42:51.999098 +08:00, CSV SHA `1406b616c804e202feb5010fd134c832bbef9a84835c498c1303f64e04677027`. It had six positive calibrations, one negative control and 59 unknowns; its original scoring policy is pre-click only. **Do not relabel v0 as strict pre-intervention.** v1 requires freeze < actual grant intervention < click. The later v0 backtest pins per-app reinstall completion and click times. v1 is not rescored in that requested v0 analysis; do not retroactively use v1 for samples already clicked before its freeze.

## Calibration and source witnesses

The user supplied the six prior permission-wall cases before this scan. Their positive forecasts are calibration, reported separately from unseen keys; they are not manufactured static detections. DEX line numbers below are from `dexdump -d` on the specified `classes*.dex`, not Java source lines. Per-app JSON retains instruction text, offset, method, lifecycle root, call path, manifest and APK hashes.

| Key | Evidence and limit |
| --- | --- |
| Wikipedia | [evidence](evidence/wikipedia.json): `MainActivity.onCreate(Bundle)`, `classes.dex:4442219`, offset `00d7`, ActivityResult bridge → `InitialOnboardingActivity`; welcome page only, not article/stable content |
| BinaryEye | [evidence](evidence/fd-binaryeye.json): `SplashActivity.onCreate(Bundle)`, `classes.dex:442168`, `000e` → `CameraActivity`, finish lexically afterward; camera function separate |
| Gallery | [evidence](evidence/fd-gallery.json): `SplashActivity.launchActivity()`, `classes.dex:2589187`, `0007` → `MainActivity`; callback reachability **unknown**, prior runtime calibration supplies the positive prediction; CE runtime required |
| FileManager | [evidence](evidence/fd-filemanager.json): `SplashActivity.initActivity()`, `classes.dex:2149616/2149620`, `002f/0038`; MainActivity class hint, Intent flow and callback reachability **unknown**; prior runtime calibration supplies positive prediction |
| Tusky | [evidence](evidence/fd-tusky.json): inherited `ie/j.onCreate(Bundle)`, `classes.dex:990034`, `013d` → `LoginActivity`, finish lexically afterward; login/onboarding/timeline own page |
| VLC | [evidence](evidence/vlc.json): `StartActivity.resume`, `classes6.dex:130649`, `02a1` → VideoPlayer; `startApplication`, line 130849, `0035` → TV onboarding; `startOnboarding`, line 478944, `0010` → mobile onboarding; CE runtime required |

## Method and limits

Reuse of the existing scanner is pinned under [v1 dependencies](freezes/v1/dependencies/) and task code under [v1 code](freezes/v1/code/). The launcher-only graph includes lifecycle roots and inherited methods, exact/unique dispatch, class initializers and local Intent factories. Register tracking resets at branches/joins; class-name hints stay separate from actual Intent targets. ActivityResult `launch(Object, options)` is recognized. Finish order is **lexical**, not guaranteed runtime order. Memoization preserved method counts, reachable counts and unresolved-edge counts for all 63 APKs available in both passes: [parity evidence](evidence/graph-parity.json).

All base-APK DEX files were scanned. Split DEX, dynamic/native navigation, framework callbacks, async paths, branch feasibility, cross-method Intent mutation and actual first-frame behavior remain unresolved. A path of at most four graph edges with an explicit non-launcher target is promoted to `advance_likely` unless its caller signature is Intent/Object-dependent; deeper or generic callbacks remain `advance_possible`. This is a ranking heuristic, not a proof that a fresh launch takes the branch. App keys are counted separately even when they share packages or versions.

Subway Surfers expected APK SHA starts `5904cda2`; available input starts `ffd32287`, so its forecast stays unknown. `x` and `noice` had null batch-manifest hashes; the exact prior JNI-inventory APK hashes were independently checked against input bytes before scanning. [Input receipt](freezes/v1/inputs.json).

## Run and later backtest

From repository root, using the existing Android SDK build-tools 37.0.0 `aapt2`/`dexdump` and local APK paths pinned in the input receipt:

```sh
python3 benchmark/2026-09-30-background-start-prospective/test_prediction.py
# Optional fresh scan; preserve prior evidence before rerunning:
python3 benchmark/2026-09-30-background-start-prospective/scan.py
# Publish only to a NEW version; never rewrite v0/v1:
python3 benchmark/2026-09-30-background-start-prospective/publish.py --version v2
```

Copy [observation-template.json](observation-template.json), then supply one homogeneous run's adjudicated observations. `grant_verified=true` means the installed synthetic HAP actually declares **and has** `START_ABILITIES_FROM_BACKGROUND`; replacing installer bytes alone is insufficient. Record exact APK SHA, timezone-qualified `intervention_at` and `clicked_at`, board/runtime/JAR fingerprint, actual selected launcher, baseline state, and evidence paths. `advance_observed` means a previously blocked transition now progresses, not merely that an Activity appeared in logs. `predicted_page_observed` needs a screenshot identifying the forecast destination UI. Missing evidence stays unknown.

```sh
python3 benchmark/2026-09-30-background-start-prospective/backtest.py \
  --freeze benchmark/2026-09-30-background-start-prospective/freezes/v1 \
  --observations /path/to/adjudicated-observations.json \
  --out benchmark/2026-09-30-background-start-prospective/backtests/run-name.json
```

The scorer verifies frozen hashes, excludes missing grant/timestamp/identity, preserves abstentions, and reports accuracy, coverage, conservative coverage-adjusted accuracy and confusion counts separately for calibration, unseen keys, negative control and runtime-profile strata. It refuses duplicate keys and output overwrite. Concurrent v3c activation, JAR replacement, launcher selection or app-data changes are confounders: record `comparable_profile=false`, report that stratum, and do not attribute all progress to authorization. The first requested v0 hit rates and their runtime-profile confounds are recorded in the linked backtest. Frozen code is an audit snapshot; run the repository entry points above, which resolve the shared scanner paths.

## Validation and handoff

[results.json](results.json) records offline checks. Three Python tests cover target flow, ActivityResult bridging, branch uncertainty, graph resolver parity, calibration separation, scoring exclusions, immutable hashes and raw backtest accounting; two Rust contract selectors call those checks. The later read-only backtest preserves the supplied screenshots and process tables; it performs no board operations. Commit is pending outer-ring submission because this worktree's shared Git metadata is read-only.
