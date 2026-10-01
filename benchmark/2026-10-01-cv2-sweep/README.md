# cv2 full sweep on three boards under U7 (2026-10-01, oc-t4)

Dispatch (board ACK(97) 09:20:27 pre-dispatch): 100 corpus-v2 keys on three boards, `master bms_batch.py --execute --reinstall --shots 5,20` under U7. This directory is a trimmed **copy** of `benchmark/2026-10-01-cv2-sweep/` (the original is kept complete with all 198 screenshots; landing copies only).

## Facts (verbatim)

### 5ea (RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards))
```
TOTAL keys=34 screenshots_captured=68/68 alive_t5=23 alive_t20=23
```

### 5cd (RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards))
```
TOTAL keys=33 screenshots_captured=66/66 alive_t5=25 alive_t20=25
```

### 61b (RUNTIME fingerprint=68b7fb016253 files=119 (runtime-fingerprint.txt; compare before blaming the JAR across boards))
```
TOTAL keys=33 screenshots_captured=64/64 alive_t5=24 alive_t20=24
```

## Outcome (outer sign-off)

Master `benchmark/2026-10-01-cv2-sweep/outer-signoff.json` (outer loop, screenshot review):
**lit 65 / lit-webview-fallback 2 / alive-not-lit 5 (alive-launcher-foreground 3 + alive-blank-window 2) / dead 27 / app_failed 1**.

## Landing notes

- Per key: `record.json` + `install.txt` only (copied from the complete original).
- Per run: `facts.txt`, `plan.json`, `baseline.json`, fingerprints, `summary.json`.
- Screenshots: **not landed** — 198 entries in `screenshots-manifest.json` (path + sha256 + bytes), pointing at the original directory which holds the recovered images.
- hilog was not captured in this sweep (see `benchmark/2026-10-01-cv2-hilog/` for the 33 non-lit keys re-run with `--hilog`).

## Outer-loop notes (master)

- The per-key t20 verdicts are `outer-signoff.json` (outer loop read all 99 t20 images; lit 65, WebView fallback page 2, alive but not lit 5, dead 27, app_failed 1).
- Screenshots are not committed (`*.jpeg` is ignored). The originals are in the westlake-harness-t4 worktree run dirs and a copy is in `$WORKSPACES/westlake-inputs/evidence-backup/2026-10-01-cv2-sweep/`; `screenshots-manifest.json` has every sha256. They were deleted once by a landing step and recovered from the boards' `/data/local/tmp/bms-batch-<run_id>/` (198/198 sha256 match), see the board R2 #97 10:59:59.
