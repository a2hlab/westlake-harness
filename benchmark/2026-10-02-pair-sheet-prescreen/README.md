# pair_sheet.py pre-screen — auto same/different/no-window + flaky k/n (sign-off accelerator)

Adds a perceptual pre-screen to `scripts/lab/pair_sheet.py` so the outer loop signs a window by eyeballing only the
suspect pairs, not all ~77. Offline, no board. Image work is ffmpeg-only (no Pillow/imagehash — not installed).

## What it does
Per pair (window t20 vs the key's U9 t20): crop the top status-bar strip (so the clock never scores as a diff),
scale to 16x16 grey, take an average-hash, and emit an `auto` verdict + `similarity`:
- **same** — aHash similarity >= threshold (default **0.86**).
- **different** — below threshold (window rendered a different screen than U9).
- **no-window** — window t20 missing, OR near-uniform AND flatter than its U9 (lost content) / a blank white render.
- **no-ref** — no U9 t20 to compare.

A **flat-but-lit** screen (e.g. a plain settings page, grey std ~1.5) is NOT no-window: blank detection is *relative*
(`std < 2.0` AND `std < 0.4 * u9_std`, or near-white with no U9), so an equally-flat U9 matches it by similarity.
Flaky-registry keys (`knowledge/gates/flaky-keys.json`) also carry `flaky_kn` = k lit / n (this window's auto +
signed history), `regression=true` on the rule (>=3 obs, 0 lit).

Output: `pair-sheet-suspects.jpeg` (only auto!=same or an undecided flaky key) + `pair-sheet-full.jpeg` (all pairs) +
`pair-sheet.json` (auto/similarity/flaky_kn pre-filled; **window_verdict stays blank** — the tool never judges
lit/white, the outer fills it, now reading only the suspects sheet).

## Calibration + known-answer (window3, 77 outer-signed pairs)
Calibrated on `benchmark/2026-10-02-u10-1-t8-rerun/window3-signoff` (76 "same screen as U9" + trickytripper
"launcher at t20 / RenderThread SIGSEGV" = different). `pair_sheet.py --selftest`:
- **77 correct, 0 wrong** at threshold 0.86.
- margin: lowest "same" similarity **0.969** (cv2-com-ei-bmicalc) vs trickytripper **0.500** — a 0.47 gap; 0.86 sits
  mid-gap (0.11 below the lowest same, 0.36 above the diff), so the threshold is not fragile.
- suspects reduced **77 → 1** (only trickytripper), i.e. the outer eyeballs 1 pair instead of 77.
- First attempt mis-flagged 18 flat-but-lit screens as no-window (absolute std gate); fixed with the relative gate
  above → 0 wrong.

## Rule set this time
A flat screenshot is not a blank screenshot — never call "no-window" on absolute stddev alone; compare to the
reference the window is supposed to match. aHash on a cropped 16x16 grey is enough to separate same/different here
with a wide margin, with zero new dependencies (ffmpeg only).

## Tests
`scripts/lab/tests/test_pair_sheet.py` — 16 tests (aHash identity/inversion, prescreen same/different/no-window/
no-ref/flat-lit, flaky k/n + regression, is_suspect, and the window3 known-answer via `--selftest`). `Ran 16 tests OK`.
