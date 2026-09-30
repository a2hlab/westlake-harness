# R16 outcome-blind forecast

Frozen **2026-09-30 00:15:05.545941 +08:00**, before any r16full A/B result access: **66 keys, 16 predicted lit, 50 predicted not lit**, including eight unknown first-wall causes with explicit low-confidence negative forecasts. Unlike the previous r15c-informed revision, these are forecasts for unseen full-sweep outcomes. The sweep had already started, so strict pre-click accuracy must be reported separately from outcome-blind accuracy.

- predictions.csv SHA-256: bb721a18824ab595086fbe57d378c5e26a3d4298b5599bad29ddc53266b1c32a
- predictions.json SHA-256: e8ce460f6a8cdfdfa13e3d885827f9aea3552cdb0b88e5be1f760995a43aa94e
- freeze.json also pins forecast.py, score.py, policy.json and predecessor inputs. SHA256SUMS covers the initial freeze files; later observations/tests/documentation are outside that original manifest.

Predicted lit: ooniprobe, aegis, fd-AppManager, fd-droidify, fd-fitness, fd-noice, newpipe, fd-calendar, fd-feeder, fd-libretube, fd-notes, fd-organicmaps, fd-reader, fd-stk, fd-client, noice. Predictions include confidence, explicit first wall or none, original observed walls, assumed mitigations and latent static alternatives. Alternatives do not count as first-wall successes.

Generation assumption: r16 6a5d7fca, appspawn d977bd15, libbms 6f94d4f4, installer eb6824b4, and per-APK reinstall with INTERNET granted in synthesized HAP. Do not assume CommonEvent #91, two-board native parity, arbitrary installation fixes or all latent JNI gaps resolved. OnlineJobScheduler/OnlineConnectivityManager and ShortcutManager are assumed to mitigate their corresponding startup requirements, which remains a falsifiable prediction.

Disclosed training context includes r15c, prior r16 sanity/controls, cc-t3's r15c Notes t10 correction and Anki launcher diagnosis. No full-sweep record/log/summary/screenshot or directory was inspected before freezing. exposure-receipt.json precedes the first full-run directory access; the complete CSV/JSON SHA was published to the campaign board first.

Run from repository root:

    cargo test --manifest-path tools/spec-checks/Cargo.toml r16_prospective
    python3 benchmark/2026-09-30-r16-prospective/collect_results.py --status
    python3 benchmark/2026-09-30-r16-prospective/collect_results.py
    python3 benchmark/2026-09-30-r16-prospective/evaluate.py \
      --observations benchmark/2026-09-30-r16-prospective/observed/observations-reviewed.json

Collection waits for 33 completed records in each shard and 66 distinct forecast keys. It emits observations-pending.json with all visual and wall labels unknown. Copy to observations-reviewed.json and fill reviewer, screenshot references and first-wall evidence after independent adjudication. Process UID rows and captured counts remain separate. Do not infer lit from survival, READY, automatic focus acceptance or log silence.

Frozen policy scores own app UI at any scheduled captured shot, including identified app loading/content-error UI. Desktop, black/blank window, system crash dialog and unrelated/debug launcher are not lit. First-wall labels describe the earliest evidenced blocker, not the final/tolerated exception. Lighting and wall scores have independent denominators. Unknown/mismatched/incomplete observations remain excluded with counts; a conservative wall metric counts unknown wall forecasts as misses. Report full outcome-blind, strictly pre-click and generation-profile strata separately.

No forecast or scoring-rule edits after exposure. Repairs, screenshots and commits are outside this offline lane's actions. R2: forecast sealed and mechanically tested; actual lighting/causality is unverified until evidence review.

## Completed sweep evaluation

Outer reviewed both scheduled frames for the completed A/B sweep (source snapshot: observed/outer-adjudication.json). **Nine keys show own UI; 130 screenshot hashes match records; 16 target-UID processes survive t5.** There is no t20 sampling. Subwaysurfers failed the APK-identity gate before launch and has no screenshots: its declared record hash is not treated as proof of the executed APK.

| Metric | Hits / denominator | Rate |
|---|---:|---:|
| Lighting, all exact adjudicated keys | 56 / 65 | 86.2% |
| Lighting, strictly clicked after freeze | 40 / 46 | 87.0% |
| Predicted-lit precision | 8 / 16 | 50.0% |
| Actual-lit recall | 8 / 9 | 88.9% |
| First wall, known observed and non-abstaining forecast | 23 / 44 | 52.3% |
| First wall, unknown forecasts counted as misses | 23 / 49 | 46.9% |
| Strict pre-click first wall, unknown forecasts counted as misses | 18 / 36 | 50.0% |

Overall lighting accuracy **equals the always-not-lit baseline (56/65)**. Do not present accuracy alone as an improvement. The confusion matrix is TP=8, FP=8, FN=1, TN=48. Of 66 keys, 46 were clicked after freeze, 19 earlier and one never clicked; only the 46 form the strictly prospective subgroup. All full-sweep outcomes were unseen at freeze, but prior sanity/control disclosures were known.

False positives: fd-droidify, newpipe, fd-calendar, fd-feeder, fd-libretube, fd-organicmaps, fd-reader, fd-client. The false negative is fd-mpv on 61b, whose native registration differs from 5cd. Foreseeing a mitigation did not establish complete startup recovery: remaining walls include foreground-service attachment, JobScheduler paths still returning null, BatteryManager, SystemVibrator, provider permission checks, and earlier native/application initialization failures. Exact rows and original evidence lines are in lighting-misses.csv and wall-misses.csv.

First-wall observations are independent post-run exception-chain judgments, not confirmed repair experiments. Prefer the earlier failed Application/provider chain over downstream null symptoms. Seven non-lit visual outcomes retain unknown first-wall causes; five unknown forecasts occur within the 49 classified observed walls and are exposed by the conservative metric. The automatic triage script remains an auxiliary artifact; it can select wrappers or unrelated system/native signals and does not decide screenshot outcomes.

Noice and fd-noice retain own UI with a network error, so the networking change did not deliver the predicted content recovery in this run. Their successful own-UI classification must not be interpreted as successful HTTP/DNS permission verification.

Machine-readable evaluation: backtest.json/csv, results.json, lighting-misses.csv, wall-misses.csv. Original forecasts, policy, scoring code and initial SHA manifest remain unchanged. Outcome receipt and supplemental artifacts are hashed separately in OBSERVED-SHA256SUMS.

The strict pre-click subset is also imbalanced: TP=3, FP=6, FN=0, TN=37; predicted-lit precision is 3/9 (33.3%), recall is 3/3, and the always-not-lit baseline is 43/46 (93.5%), above the model's 40/46 (87.0%). These small positive denominators and the weaker baseline comparison are part of the result, not grounds to revise the sealed forecast.
