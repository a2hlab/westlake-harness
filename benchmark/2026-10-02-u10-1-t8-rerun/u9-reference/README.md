# U9 reference contact sheets (for the U10.1-T8 window predict_vs_actual)

Per-board U9 (j10g baseline) t20 contact sheets, tiled in the **exact stage-A key order** so the outer loop
can read the U10.1-T8 window result side-by-side against the signed U9 baseline, cell by cell.

## Images (git add -f per AGENTS — jpeg is gitignored, README-referenced evidence is force-added)
- `u9-ref-5ea.jpeg` — 56 tiles, 2 missing (`toutiao` dead, `cv2-com-frequent-habits` app_failed)
- `u9-ref-5cd.jpeg` — 55 tiles, 0 missing
- `u9-ref-61b.jpeg` — 55 tiles, 0 missing

Each is `--cols 7`, portrait tiles. Homebrew ffmpeg lacks the drawtext filter, so tiles are **unlabeled in the
image**; read each cell's app from the matching `u9-ref-<board>.txt` by grid row/col.

## Listings (grid row/col -> key -> U9 verdict -> source)
`u9-ref-5ea.txt`, `u9-ref-5cd.txt`, `u9-ref-61b.txt` — one line per cell:
`row R col C  <key>  verdict=<U9 t20 verdict>  corpus=<original|cv2>  <real U9 t20 source or MISSING>`.
Row/col match the jpeg grid. Verdict is the outer-signed U9 t20 verdict (lit / dead / alive-white-window /
alive-black-window / alive-black-content / app_failed / alive-launcher-foreground).

## How this was built (offline, read-only, no board)
- **Key order**: concatenation of the stage-A shard keys_files named in
  `benchmark/2026-10-02-u10-1-t8-rerun/window/plan-{5ea,5cd,61b}.json` shard order
  (toutiao-gain, lit-original, lit-cv2, unlit-original, unlit-cv2). Duplicates dropped keeping first.
- **Screenshots**: each key's `t20.jpeg` from the U9 sweep runs recorded in
  `benchmark/2026-10-01-u9-sweep/outer-signoff.json` `runs` ($WORKSPACES-expanded; each board's own runs only).
  A key with no `t20.jpeg` in its board's U9 run → grey "(missing)" tile, written `MISSING` in the listing;
  **not substituted from another run**.
- **Tiling**: `scripts/lab/contact_sheet.sh <out> --cols 7 <key.jpeg>...` with per-key symlinks named by key
  so the grid order is the plan order and the stdout/listing label is the key.

## Verdict tallies (U9 baseline)
- 5ea: lit 37, dead 14, alive-white-window 2, alive-black-content 1, app_failed 1, alive-black-window 1 (56).
- 5cd: lit 38, alive-white-window 8, dead 9 (55).
- 61b: lit 40, dead 9, alive-white-window 4, alive-black-window 1, alive-launcher-foreground 1 (55).

Use: when the U10.1-T8 window t20 sheets land, diff each cell against these; a cell that was `lit` here and is
not lit there is a regression; an `alive-white-window` here that lights there is a gain.
