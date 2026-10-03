# U14 signing reference (126 lit)

U14 baseline = U13's 122-lit reference + 4 U13 stage-A lit gains + fd-seal t20 refresh.

## Composition

| Layer | Keys | Provenance |
|---|---|---|
| U13 122-lit base | 121 untouched | `benchmark/2026-10-03-u13-reference` (grid order + t20s unchanged) |
| + stage-A gains | fd-noice, fd-uhabits (5ea, 6/6 lottery each); noice, cv2-com-lcdcode-moodcairns (61b, 1/1 each) | t20 = the pair-sheet run that carried the signed verdict (window1 last lottery run; window2-61b) |
| + fd-seal t20 refresh | fd-seal (61b, verdict already lit) | window4 seal-only run: paints the Seal main UI behind the guide dialog; old reference showed a blank background |
| **Total lit** | **126** | 122 + 4 gains (fd-seal stays lit, only its t20 moves) |

`fd-noice` was U13 `lottery` and `fd-uhabits` / `noice` / `cv2-com-lcdcode-moodcairns` were `alive-white-window` / `alive-white-window` / `dead` on U13 — all four re-signed lit in U13 stage-A (window1/window2 outer signoffs).

## Files

- `build_reference.py` — overlay builder over the master U13 reference (read-only inputs)
- `sources.json` — per-key provenance (board / plan_shard / verdict / windows / picked / run_board / run_shard / t20 + t20_sha256), tallies, total_lit
- `u14-ref-<board>.txt` + `u14-ref-<board>.jpeg` — grid order + contact sheet (cols 7), unchanged tiles keep U13 t20s; changed rows marked `*gain` / `*t20-refresh`
- `known-answers/verify_reference.py` — checks lit == 126 and every lit key's t20 exists with the recorded SHA (non-lit keys without t20 are informational, inherited from the base grid)

## Known answer

`python3 known-answers/verify_reference.py` → `lit count: 126 (want 126)` / `checked 166 keys; lit problems: 0; non-lit without t20 (info): 1` (the 1 is cv2-com-frequent-habits, `app_failed`, inherited from U13).

pair_sheet usage (master scripts):

    python3 scripts/lab/pair_sheet.py --run <U14 run> \
        --reference benchmark/2026-10-03-u14-reference \
        --signoff <stage-A outer-signoff.json> --out <scratch> --no-sheet
