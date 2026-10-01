# U8 three-freeze scoring preparation

## Evidence and corrected rules

A signed t20 class is not an exception root, a successful API checkpoint, or installed APK byte attestation. Treating an ActionBar risk tier as predicted death, counting `unknown` as a negative, or padding an incomplete replay with old outcomes would fabricate accuracy. This scorer keeps those boundaries explicit.

`score.py` reads all three immutable predictions in one invocation. It verifies their full SHA256, joins by key, verifies package/APK SHA agreement across freezes, and rejects wrong signoff authority/schema, key cohort, verdict totals, runtime/image, or duplicate attempts before emitting results. Formal U8 requires 166 unique keys and `RUNTIME=e953c0921536`, `BOOTIMAGE=4db882a81732`. The signoff is the outer review authority, not a new screenshot review by this script.

| Freeze | Keys | SHA256 | Timing / scoring scope |
|---|---:|---|---|
| cv2 v1 | 100 | `ab51ab2df4fa6d8e66989d8713da71b79ef5e9c9e6b473f6c54a4bd1d1bc21b1` | Original late freeze; 73 own-ui, 27 abstentions; first-wall/checkpoint predictions unknown |
| ActionBar | 166 | `c115d17cd826c479c2f549b2b9e0e92825a4029cab1383079fe601276add12bd` | U7 retrospective risk inventory: 21 startup/calibrated-first-content, 28 later-only, 117 other; no frozen binary t20 forecast |
| WebView | 7 | `94d701664e337bd6f4c1544704927a60a331d0b6a4dcffae3fbfce1f7e08e66b` | Late: 11:34:35 after rollout LOCK 11:29:25; five dead, two fallback forecasts; not relabeled pre-deployment |

All baseline and input SHA bindings are recorded in `SCORING.json`. Old 66 use `u7-scoring/formal-66/reviews.json` (34 app-owned UI), cv2 uses its signed six-class review (65 functional lit + two fallback). U7 desktop/white/black labels remain coarse; they are not silently reclassified as process death/aliveness. Old 66 do not have a reliable functional-WebView baseline, so that secondary change axis remains unknown.

## Formal invocation after outer signoff

From repository root:

```sh
python3 benchmark/2026-10-01-u8-scoring-prep/score.py \
  --signoff "$WORKSPACES/westlake-harness/benchmark/2026-10-01-u8-sweep/outer-signoff.json" \
  --output /tmp/u8-formal-scoring
```

Use the actual outer-supplied signoff location if different. Output: `SCORING.json`, `SCORING.md`, `CHANGES.csv`, `CV2.csv`, `ACTIONBAR.csv`, `WEBVIEW.csv`. Input refusal exits 2; successful publication exits 0. `CHANGES.csv` contains all 166 keys, signed baseline authority, app-owned `new-lit/regression/unchanged`, and a separate functional upgrade/regression axis. An HTML-fallback screen counts as app-owned UI but not functional lit.

For raw termination evidence, append one or more `--run-root /path/to/selected-signed-run` arguments. Select only signed attempts, not overlapping parent/retry folders. Duplicate attempts are rejected rather than automatically choosing the latest. Records must match frozen package/APK SHA; runtime/image fingerprints in the nearest complete ancestor `facts.txt` must match the signoff. Missing facts or hilog leaves root unknown; conflicting facts reject the input. This is a record/fingerprint binding, not fresh installed-byte attestation. Only these matching logs go through `first_fatal.load_run/analyze`, using target PID and termination-linked exception/crash chains; caught or unrelated context cannot supply a wall.

## Three axes, not one accuracy number

- cv2: own-ui/unknown × six signed classes. Precision is reported separately for functional lit and app-owned lit including fallback. Unknown contributes abstention, not TN/FN; binary accuracy is undefined. Its frozen first-wall/checkpoint axes stay abstentions.
- ActionBar: startup and later-only class counts, change counts, and 22 previously-lit later-only controls. A lit first screen does not disprove a later-only call. Terminal-linked ActionBar roots are reported as observed family evidence, not proof of exact predicted Activity/callsite or successful later-page exposure. Without page-exercise receipts, exposure/checkpoint remains unknown; binary accuracy stays undefined.
- WebView: exact six-class t20 confusion and hits, independently from next-wall family evidence. Optional terminal-linked settings/Capacitor families yield provisional family-hit/mismatch pending callsite review; a different wall does not prove the provider checkpoint passed. A successful provider requires positive API-execution evidence, never absence of its old failure.

## Structure replay, not U8 results

```sh
python3 benchmark/2026-10-01-u8-scoring-prep/score.py \
  --signoff "$WORKSPACES/westlake-harness/benchmark/2026-10-01-cv2-sweep/outer-signoff.json" \
  --replay-cv2 --output /tmp/u8-cv2-replay
```

`replay/` publishes this exact 100-key cv2 fixture. It requires U7 state `68b7fb016253/8fe2e5fd7d65` and is explicitly `formal=false`, `mode=cv2-structure-replay-not-U8`. Changes: 100 unchanged, **66 unobserved**, not fabricated unchanged. cv2 own-ui row is `[54,2,3,0,14,0]`; unknown row `[11,0,0,2,13,1]` in six-class order. Functional precision 54/73, app-owned precision 56/73. WebView fixture exact-class agreement 5/7 is old-U7 calibration only, not U8 prediction performance. ActionBar observed counts in the fixture cannot score absent old keys. Actual U8 scores are deliberately not published here.

## Checks and landing

`test_score.py` covers immutable input drift, incomplete/duplicate cohorts, runtime and authority refusal, fallback/unknown distinctions, coarse baseline preservation, later-page boundaries, terminal-only families, raw record/facts binding, duplicate attempts, target-PID exception chains and diagnostic hash drift, and CLI outputs. Four Rust selectors wrap 17 Python tests. `validation.json` records isolated fixed-master gates and known-answer suites. `landing-paths.txt` contains only this task's new files; apply exact shared Layout/DIGEST lines from `documentation.json`, not whole copies of this worktree's shared files.
