# v0 backtest: 5ea background-start grant

**The page forecast was too optimistic: 1/5 calibration page predictions hit (20%), while Activity-transition progress hit 4/5 (80%).** Authorization removed one gate; it did not establish the destination Activity's framework fields, initialization or first frame. [Machine-readable table](backtest.csv), [scores](results.json), [selected observations](observations.json), [excluded case](excluded.json), [source hashes](source-hashes.json).

The frozen v0 CSV remains `1406b616c804e202feb5010fd134c832bbef9a84835c498c1303f64e04677027`, frozen **02:42:51.999098 +08:00**. All seven actual clicks below are later. Per-app successful reinstall completion precedes each click, APK hashes match v0, bundle dumps declare the permission with state 0, and outer confirms the grant. Successful transition logs independently show `canStartAbilityFromBackground:1`. This follows **v0's pre-click policy**, not v1's stronger pre-intervention policy. No forecast was revised after outcomes arrived.

| Key / v0 group | Click (+08:00) | Progress | Destination page | Result |
| --- | --- | --- | --- | --- |
| FileManager / calibration | 02:53:04.630974 | yes | yes | Both hit; outer accepts new own UI |
| BinaryEye / calibration | 02:58:12.367213 | yes | no | Progress hit, page miss |
| Gallery / calibration | 02:56:36.190173 | yes | no | Progress hit, page miss |
| Tusky / calibration | 02:57:24.742248 | no | no | Both miss |
| VLC / calibration | 02:59:03.667074 | yes | no | Progress hit, page miss despite no t5 process |
| Anki / unseen | 02:52:19.665754 | yes | no | v0 unknown on both axes: abstention, not a hit or false negative |
| Wikipedia / calibration | 02:51:32.120703 | excluded | excluded | Outer explicitly excludes r17g provider class-loader regression |

Calibration coverage is 5/5 after Wikipedia's explicit exclusion. Unseen coverage is **0/1**, so unseen accuracy is **undefined**, not 0% or 100%. Across the six selected cases, classified coverage is 5/6; conservative accuracy including abstentions is 4/6 for progress and 1/6 for pages. Termux negative control was not in these two runs and is not scored. Untested keys retain missing observations, not negative outcomes. Calibration page TP=1, FP=4; progress TP=4, FP=1. The all-negative page baseline would score 4/5 on this selected calibration set; this forecast does not outperform it.

## Why predictions missed

Evidence links below contain compact verbatim excerpts with **original hilog line numbers**; full input logs are pinned by SHA in `source-hashes.json`. Screenshots are outer-adjudicated; FileManager's positive image was also inspected locally. No automatic `pending_review`/focus flag was promoted into a visual verdict.

| Key | Evidence and diagnosis | Prediction error |
| --- | --- | --- |
| FileManager | [log](evidence/fd-filemanager/hilog-excerpts.txt): source lines 32322/32333 dispatch `MainActivity`, return 0; line 32337 confirms background grant. [t20 image](evidence/fd-filemanager/t20.jpeg) shows app toolbar, add button and file/recent/storage tabs. | Correct destination-page prediction; empty content does not prove file-operation functionality. |
| BinaryEye | [log](evidence/fd-binaryeye/hilog-excerpts.txt): source lines 27805/27818 dispatch `CameraActivity`, return 0; line 43592 throws `Unable to resume activity ... CameraX is not configured properly`. [t20](evidence/fd-binaryeye/t20.jpeg). | “Camera functionality separate” was an invalid shortcut: CameraX initialization runs during resume and prevents even the page. The surviving PID 29654 is the initial process; destination PID 29714 throws before t5. |
| Gallery | [log](evidence/fd-gallery/hilog-excerpts.txt): source lines 34231/34242 dispatch `MainActivity`, return 0; line 56886 throws `NoSuchFieldError` for `MediaStore.Images.Media.EXTERNAL_CONTENT_URI` from `adapter-mainline-stubs.jar`. [t20](evidence/fd-gallery/t20.jpeg). | A present framework class is insufficient: required member coverage in the destination Activity was not a page-forecast gate. Initial PID 26449 survives; destination PID 26511 throws. |
| Tusky | [log](evidence/fd-tusky/hilog-excerpts.txt): source lines 26273/26319 show missing `com.android.org.conscrypt.OpenSSLProvider` / `Sun provider not found`; line 44203 exits through `NoClassDefFoundError: kk.e`. No target `OH_AbilityMgrClient StartAbility` is captured. [t20](evidence/fd-tusky/t20.jpeg). | Prior permission denial was assumed to remain the first blocker. Current provider initialization fails earlier, before the predicted transition. This is also a runtime-profile confound, not evidence that the new permission failed. |
| VLC | [log](evidence/vlc/hilog-excerpts.txt): source lines 31030/31042 dispatch `OnboardingActivity`, return 0; line 33545 reports `AudioSystem.native_getMaxChannelCount` ULE; line 34276 exits through coroutine initialization failure, with `Sun provider not found` / missing OpenSSLProvider at 34315/34319. [t20](evidence/vlc/t20.jpeg). | Dispatch and survival were incorrectly coupled in the initial verbal outcome summary; dispatch **did** advance. AudioSystem JNI and crypto/provider initialization remain separate observed failures; this evidence does not prove the former caused the latter. |
| Anki | [log](evidence/anki/hilog-excerpts.txt): source lines 29226/29237 show `IntentHandler` → `DeckPicker`, return 0; line 52022 destination PID 18548 throws `lateinit property instance has not been initialized`. Earlier 26832/39885 show `librsdroid.so` cannot resolve `liblog.so`. [t20](evidence/anki/t20.jpeg). | v0 had no non-calibration forecast, so this is a coverage gap. Even the full static scan retained unknown Intent flow at `IntentHandler.a(Intent)`; launcher selection changed concurrently. Surviving initial PID 18481 does not mean the destination initialized. |
| Wikipedia | [log](evidence/wikipedia/hilog-excerpts.txt): source lines 46057/46081/46086 show initializer failure and `SecureRandom (provider: BC) cannot be found`; no target transition captured. | Excluded by explicit outer instruction, recorded transparently; do not convert it into a successful permission forecast. |

Future page predictions need evidence for destination `onCreate`/`onResume` dependencies (including **fields** and initializer/provider loading), not just a launcher transition. Current framework-profile compatibility must be a prerequisite. Unresolved paths remain unknown; these observations must only affect a **new** forecast, never v0/v1.

## Counts and causal limit

Directly counting `record.json` entries with `captured=true` gives **14 captures across 7 apps**. All 14 local bytes match the recorded screenshot hashes. UID-matched process tables give **4/7 apps alive at t5 and t20**, comprising **5 app processes** at each sample; FileManager additionally has one same-UID `sh` helper, which is excluded from the app-process count. See each app's `counts.json` and copied `processes-t5.txt` / `processes-t20.txt`. The visual acceptance is **1/6 non-excluded apps**, from outer's judgments, not from those counts.

Both runs use JAR `a35a782e0ad255e25b4dbb9f0d84baa3c95a9730bc8e80120163735e21ba10f2`, runtime `7e1fd94e5d3e64e2fc86e55f9fa8c70af8cb4cfd4299c69e0fc06fbc233e2028`, and bridge `84695d62...` ([fingerprint](evidence/vlc/runtime-fingerprint.txt), source lines 50/53/68). They are placed in the **profile-mismatch** stratum relative to the disclosed earlier calibration; Anki additionally has a launcher-selection change. Thus 80%/20% are observed end-to-end forecast scores for this run, not a controlled estimate of permission-only efficacy. The provider regression also affects Tusky/VLC; unlike Wikipedia they remain in the requested denominator. Excluding them after seeing failure would inflate the score.

## Reproduce

From repository root, repackage read-only source artifacts into a fresh output directory:

```sh
python3 benchmark/2026-09-30-background-start-prospective/replay_bglaunch.py \
  --source /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-bglaunch-5ea/runs \
  --out /tmp/bglaunch-v0-replay
```

Or rescore the preserved selected observations using the unchanged scoring rules:

```sh
python3 benchmark/2026-09-30-background-start-prospective/backtest.py \
  --freeze benchmark/2026-09-30-background-start-prospective/freezes/v0 \
  --observations benchmark/2026-09-30-background-start-prospective/backtests/v0-bglaunch-5ea/observations.json \
  --out /tmp/bglaunch-v0-rescore.json
```

The packaging script is explicitly **post-outcome** analysis, outside both frozen code snapshots. Wikipedia's exclusion and outer's visual judgments are recorded inputs. Commit the referenced screenshot evidence with `git add -f`; shared Git metadata is read-only in this lane, so outer submits.
