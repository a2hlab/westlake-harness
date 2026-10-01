# Corpus-v2: immutable late-freeze scoring

The earlier lightweight/native-free hypothesis was not a runtime safety proof.
Comparing the predicted total (73) with the observed app-owned total (67) hides
17 positive mistakes and 11 successful abstentions. The rule established here:
join every signed key, keep unknown as abstention, and score functional UI
separately from an app-owned fallback page. Do not turn static calls into fatal
causes or blanket rejection rules.

## Evidence first

- Frozen CSV: `../2026-10-01-corpus-v2/apk-scan-v1/PREDICTIONS.csv`, SHA256
  `ab51ab2df4fa6d8e66989d8713da71b79ef5e9c9e6b473f6c54a4bd1d1bc21b1`.
  All v1 files are unchanged.
- Outer source: master `5641749091f0a12f084494f8e173ce75c04e05ee`,
  `benchmark/2026-10-01-cv2-sweep/outer-signoff.json`, signed
  `ACK(97) 2026-10-01T09:56:21+0800`. Source SHA256
  `01a25763077dff2d57e1cb90d8d8480c417efe7578be1b0509e3129592a42cf1`.
  Local `outer-signoff.json` adds exactly one final newline, otherwise identical;
  both hashes are enforced by the scorer.
- `run-evidence.json`: all 100 exact keys/packages/APK SHA/version and signer
  receipts agree with the pinned input; sidecars remain empty. All 99 first
  scheduled t20 screenshot files were read and SHA-verified. Frequent Habits
  has an `app_failed` record and no screenshot. Visual labels remain the outer
  reviewer's, not a foreground/alive heuristic.
- Three original `facts.txt` receipts agree on RUNTIME `68b7fb016253`, BOOTIMAGE
  `8fe2e5fd7d65`, frozen checks `4/0`, and manifest prefix `d5451a89` (the full
  input hash is pinned in v1 FREEZE.json). These are recorded short fingerprints,
  **not** a fresh per-file device-byte audit. No device action was performed.
- Original run folders contain **0 hilog.txt and 0 diagnostic receipts**.
  This signoff is sufficient for t20 label scoring, not causal first-wall scoring.
  oc-t4's subsequent diagnostic reruns are separate observations; they must not
  overwrite these signed t20 results or manufacture original-run fatal points.
- **Late freeze, not held-out:** frozen at `2026-10-01T01:46:24.262690+00:00`
  (09:46:24 local), after the first device window at 09:24:47 local. The lane's
  original receipt states it had not read cv2 logs/screenshots before freezing;
  that does not make this a prospective/held-out experiment.

## Two-by-six confusion table

| Prediction | lit | lit-webview-fallback | alive-launcher-foreground | alive-blank-window | dead | app_failed | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| own-ui | 54 | 2 | 3 | 0 | 14 | 0 | 73 |
| unknown (abstention) | 11 | 0 | 0 | 2 | 13 | 1 | 27 |
| Total | 65 | 2 | 3 | 2 | 27 | 1 | 100 |

- Coverage: **73/100 = 73%**; 27 abstentions.
- Functional positive precision: **54/73 = 73.97%**; 19 functional overpredictions.
- Literal app-owned UI positive precision: **56/73 = 76.71%**; 17 overpredictions.
  The two WebView fallback pages count only in this inclusive measure.
- 11 functional-lit keys were not positively predicted. These are underconfident
  abstentions, **not false negatives**: v1 never predicted a negative class.
  TN, FN and binary accuracy are intentionally null, not invented by treating
  unknown as unlit. No scalar "accuracy" with 27 abstentions counted as hits.
- First-wall/checkpoint: 100 unknown predictions on each axis. A visual verdict
  cannot establish a fatal chain or positive checkpoint crossing.
- Nima Task Manager remains `lit`, per the outer's explicit empty-list/FAB note.

`SCORING.json` includes all 100 rows, provenance, both UI targets, exact matrix,
per-key scanner mechanism and linked run/screenshot evidence. `SCORING.csv`
provides a compact join. `FEEDBACK.json` records candidate cohorts and ablations.

## Misclassification attribution, not invented root causes

| Cohort | Count | Scanner mechanism | Treatment |
|---|---:|---|---|
| own-ui → dead | 14 | Low-static-transfer UI prior; conditional service/context/JNI alerts are not runtime safety guarantees; three-hop exact-target startup omits dispatch/callback/reflection/resource behavior | Actual terminal/root/API match unknown pending target-PID evidence |
| own-ui → alive launcher | 3 | Startup transition candidates were not confidence guards; callback/window/screen ownership unresolved | Report exact startup transitions for Memory/Yahtzee; Acrylic has no bounded transition witness, so cause stays unknown |
| own-ui → fallback | 2 | `webkit` prefix pooling represented hundreds of calls by utility APIs; a representative off-startup API did not prove absence of content WebView use | v2 independently rescans exact content APIs and retains separate fallback target |
| unknown → lit | 11 | Whole-package native guard, coverage-selection Compose/WebView/GL group, bounded specialized-rendering or unresolved binding guards | List actual guard reasons per key; success does not prove every referenced API/ABI works, so no label-derived upgrades |

The 14 positive dead keys: `cv2-com-trianguloy-clipboardeditor`,
`cv2-com-chessclock-android`, `cv2-com-ath0-rpn`, `cv2-com-woefe-shoppinglist`,
`cv2-com-emmanuelmess-itsdicey`, `cv2-com-tomatodev-timerdroid`,
`cv2-com-aptasystems-dicewarepasswordgenerator`, `cv2-com-nbossard-packlist`,
`cv2-com-deva-knot`, `cv2-com-maxistar-textpad`, `cv2-com-nononsenseapps-notepad`,
`cv2-com-codedead-advancedpassgen`, `cv2-com-codedead-deadhash`,
`cv2-com-better-alarm`.

Three alive-launcher positives: `cv2-anupam-acrylic`,
`cv2-org-secuso-privacyfriendlymemory`,
`cv2-org-secuso-privacyfriendlyyahtzeedicer`.
Fallback positives: `cv2-com-paultirk-yatoo`, `cv2-ca-vaults-randomlydie`.
All 11 successful abstentions and their exact original guards are in SCORING.json;
they are not counted as missed fatal signatures. In particular Compose/native
presence alone was conservative, not a measured incompatibility.

## Scanner v2 and negative controls

New version: `../2026-10-01-corpus-v2/apk-scan-v2/`. It uses no observed labels
as classification inputs. All 100 APKs and 136 DEX members were independently
rescanned against the same APK/DEX hashes and dexdump binary. Exact content
calls are no longer pooled with `MimeTypeMap`/`Linkify` utility APIs.

| New candidate | Apps | Signed classes within candidate cohort |
|---|---:|---|
| webview-content-contract | 15 | 9 dead, 3 lit, 2 fallback, 1 blank |
| startup-activity-transition-contract | 32 | 26 lit, 4 dead, 2 alive launcher |
| startup-koin-contract | 1 | 1 dead; actual fatal Koin root still unknown |

There are 46 distinct candidate-bearing apps (cohorts overlap). These are
**candidate-only rules**, not death predictions or admission failures.
Three real signed-lit optional-content controls are Notally, Pixel Studio and
Timetable; Privacy Friendly 2048 is a signed-lit startup-transition control.
Bizzle is a signed-lit no-added-contract control. Memory's utility webkit
calls do **not** satisfy the content rule (its separate startup transition does).
Unit fixtures additionally exclude MimeTypeMap, WebSettings and unrelated
same-named WebView classes.

The deliberately tested blanket-abstention ablation demotes 35 original positives:
8 functional overpredictions, **but also 27 genuine functional-lit positives**.
Remaining positives: 38, of which 27 lit, 10 dead, 1 alive launcher. Precision
falls to **27/38 = 71.05%** from 73.97%; coverage falls from 73% to 38%.
Therefore the blanket guard is **not promoted**. Default v2 keeps the original
73/27 t20 hypotheses and exposes precise candidate evidence; its additional
`abstention_experiment_t20` column is explicitly retrospective/unpromoted.
No new freeze or held-out improvement is claimed. The remaining 11 experimental
positive-unlit keys are enumerated in FEEDBACK.json for future evidence-led work.

## Reproduce and hand off

From the repository root:

```sh
python3 benchmark/2026-10-01-cv2-scoring/score.py --output /tmp/cv2-score
python3 benchmark/2026-10-01-corpus-v2/apk-scan-v2/report.py --output /tmp/cv2-static-v2
python3 benchmark/2026-10-01-cv2-scoring/test_score.py
agent-spec lifecycle specs/cv2-scoring/t1-score.spec.md --code tools/spec-checks --min-score 0.7 --format json
```

`capture.py` can re-audit private original run files via WORKSPACES; checked-in
compact receipts permit scoring replay without those files. `collect.py`
documents the actual APK re-scan command in the v2 README. See `validation.json`
for completed checks and the fixed-master isolated overlay. Use `landing-paths.txt`
and `documentation.json`, not whole-copy replacements of shared README/DIGEST.
No frozen v1 file or existing selector is modified; no device/push operation.
