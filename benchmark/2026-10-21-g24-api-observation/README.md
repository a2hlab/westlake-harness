# G25 — append the G24 loader trial as observation 60 (no game-status upgrade)

The current API observation table (`../2026-10-19-api-progress-update/`) gains **one** row. Its 59-row
prefix is byte-for-byte the objects of master `b2d14677a6` (`original-59.json`, pinned in
`input-pins.json`). The historical 315 atlas, the renderer `render.py` (`0276c50e…`), the G15/G17 results
and all prior README lines are unchanged; README only gains one appended paragraph.

Row `OBS-20261021-G24-GLES-LOADER-TRIAL` ([added-row.json](added-row.json)) records what the G24 receipts
say:

- Candidate libnativeloader `878c7019…` adds only `libGLESv2.so` to the shared names of baseline
  `b8be63d2…`. Apply rc0, one ordinary icon launch, then rollback rc0.
- The original libyuanshen→libGLESv2 missing-library error is absent, and relocation now fails at
  `__register_atfork`. This is bounded loader progress, **not** GLES completion or game use.
- The game went white and returned to the desktop, child exit code 1. `game_frames_observed=false`.
  `__errno` (pre-existing) and the Unity `nativeRestartActivityIndicator` UnsatisfiedLinkError remain.
  Game child maps were not captured.
- The device is on the **restored baseline** (319/319 targets equal, mount stack and Boat3 equal, power
  restored, lock released 20:43:19). The candidate is not the current deployment. One app only: no
  public-API freeze, no two-app validation, no Genshin playability.
- References are 5 source, 9 build and 16 evidence files, all exact SHA:
  - source chain: `gles-loader-candidate` (patch, baseline/candidate sources, recipe, toolchain
    identity, build receipt);
  - build archive `9b3f27bd…` and G24 execution archive `57b760d3…`, both remote-SHA-verified (large
    raw logs stay in the archives);
  - G24 evidence: `gles-window02/closed` and `launch-review-01`.

## Checks (offline; `check.stdout.txt`, rc 0)

`python3 -B check_observation.py [--source-root <repo>]` (or `cargo test --test commercial_game_g24_observation`):

- **Prefixes and renderer.** It reuses G17's checker. G15's 58-row prefix and G17's 59-row prefix are
  now checked strictly and later rows are allowed; the renderer's 60-row CSV/HTML/results are
  consistent, with 1388 references.
- **Row 60.** It must equal `added-row.json`, plus independent semantic guards (no frame, restored
  baseline, not frozen, not GLES-complete). It is cross-checked against the G24 receipts, and both
  archives must be remote-verified.
- **Renderer byte check (revision after peer review of `8b0b38c7`).** A byte-identical copy of the
  original `render.py` (SHA `0276c50e…`) is run in a temp mirror on the checked JSON. The committed
  `index.html`, `observations.csv` and `results.json` must equal its output byte for byte, which covers
  body text, status, links and SHAs. G25 requires exactly 60 rows.
- **Twelve negative cases are refused:**
  - history object changed, G17 row changed;
  - game success, candidate as current deployment, freeze, row-60 edit;
  - missing reference, SHA drift;
  - truncation to 59 rows, 61 rows, 61 rows with an unverified missing reference;
  - **HTML-only status forgery**: row 60 changed to "GAME_PLAYABLE；有游戏帧；候选当前部署" with JSON,
    article count and IDs unchanged.

  The peer showed that `8b0b38c7`'s checker still passed that last forgery, so its earlier
  "html_csv_consistent" claim was too strong. That commit's content was correct and is kept as history.

The G17 checker change is minimal: the row count goes from `== 59` to `>= 59` with a strict prefix;
render counts follow the actual row count; the obsolete "rejects 60" negative case becomes "row 59
changed". G17's results and other SHA256SUMS lines stay at their delivery values; only its
`check_observation.py` line is updated.

No device, REA, build, G14 or T38 content was run. Not pushed.
