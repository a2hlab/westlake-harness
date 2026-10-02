# U13 signing reference: pair the U13 window against the U12 122-lit baseline, not U10.1T8

U13 signing compares each U13 window t20 with the latest signed baseline. That baseline is **U12's 122-lit state**, not
U10.1T8's 116. The two differ by six keys, all already outer-signed:

- **5 gains** that U12 stage-A window 4 signed **lit** (all `dead` on U10.1T8): `fd-client` (Nextcloud onboarding),
  `cv2-com-kaajjo-libresudoku` (LibreSudoku board), `cv2-com-trianguloy-clipboardeditor` (floating editor),
  `cv2-com-nbossard-packlist` (trip list + FAB), `cv2-com-nononsenseapps-notepad` (welcome note). Source:
  `benchmark/2026-10-02-u12-final-assembly/window4-signoff/outer-signoff.json` (`gains_vs_u10_1_t8`).
- **itsdicey** (`cv2-com-emmanuelmess-itsdicey`), re-signed **lit** (`cb7e105ffa`): its idle screen is opaque black by
  design (`DiceView.onDraw` → `drawARGB(255,0,0,0)`), not a render fault. U10.1T8 had scored it `alive-black-content`.

116 + 5 + 1 = **122 lit**. Against U10.1T8 a U13 window would flag these six as "different" every time. This directory
is the same per-board format as `benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference`, built as an overlay on it.

## What is here

**Per board** (same format pair_sheet parses; 55 / 55 / 56 keys = 166):
- `u13-ref-{5ea,5cd,61b}.txt`: one line per cell —
  `row R col C  <key>  verdict=<U13 baseline>  corpus=<original|cv2>  <real t20 path or MISSING>`.
  - Key order and row/col = the U10.1T8 reference grid (= the U12 `plan-<board>.json` shard concatenation). **The 116
    lit tiles keep their U10.1T8 t20.** Only the six changed keys move: the 5 gains take their **U12 window-4** t20;
    itsdicey keeps its own U10.1T8 t20 (same screen; only its verdict flips to lit).
- `u13-ref-<board>.jpeg`: `contact_sheet.sh --cols 7`, unlabelled tiles (read the cell from the txt).

**Shared files:**
- `sources.json`: per key, its baseline verdict, the run that carried it, the t20 path + sha256, and a `source`
  (`u10-1-t8`, `u12-window4`, or `u10-1-t8 re-sign (cb7e105ffa)`). `total_lit` = 122; `tallies` per board.
- `build_reference.py`: regenerates everything as an overlay (U10.1T8 reference + the U12 window-4 pair-sheet for the
  gains' t20); stdlib only. `--no-sheet` skips the jpegs.
- `known-answers/pair-sheet-u12-window4.txt`: the pair_sheet run below.

**Verdict tally (= the 122-lit baseline):**

| board | keys | lit | from U10.1T8 | newly lit here | other verdicts |
|---|---|---|---|---|---|
| 5ea | 55 | 40 | 37 | +3: libresudoku, clipboardeditor, itsdicey | dead 11, lottery 1, alive-white-window 1, app_failed 1, alive-black-window 1 (1 MISSING t20: frequent-habits) |
| 5cd | 55 | 39 | 38 | +1: fd-client | alive-white-window 8, dead 8 |
| 61b | 56 | 43 | 41 | +2: packlist, notepad | dead 7, alive-white-window 3, white 2, alive-black-window 1 |

Lit 40 + 39 + 43 = **122**. The one MISSING t20 is `cv2-com-frequent-habits` (app_failed), exactly as on U10.1T8.

## Which t20 (no judgment, no substitution)

Each reference t20 is the real run t20 that carried the signed verdict (`sources.json` `picked`/`t20`/`t20_sha256`):
- the **116** unchanged keys → their U10.1T8 run t20 (copied from the U10.1T8 reference);
- the **5 gains** → their U12 window-4 run t20 (`.../window4/u12-A4-20261003T002941/<board>/runner/<shard>/.../t20.jpeg`),
  the run the outer read as lit in window-4;
- **itsdicey** → its own U10.1T8 window-5 t20 (unchanged black screen); only the verdict flips.

Nothing else is borrowed or substituted; a run without a t20 is `MISSING` (grey tile), never another run's t20.

## Known answer (`known-answers/pair-sheet-u12-window4.txt`)

Pairing the **U12 window-4 run** against this reference, with master's `pair_sheet.py` (the one that reads
`<label>-ref-<board>.txt`; U13 signing runs on master):

```
pair_sheet.py --run $WORKSPACES/.../window4/u12-A4-20261003T002941 \
              --reference benchmark/2026-10-03-u13-reference \
              --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json
```

| | same | different | no-window | **no-ref** |
|---|---|---|---|---|
| vs **this U13 reference** | **40** | 1 | 2 | **0** |
| vs U10.1T8 reference (was) | 35 | 6 | 2 | 0 |

The **5 gains flip different → same** (`sim=1.0`, `verdict=lit`) — the reference t20 is that run's own t20 — and
**no-ref stays 0**, exactly the outer's predicted answer. The 3 remaining non-same pairs are all expected (per the U12
window-4 signoff): `frequent-habits` (app_failed, no t20 — the one MISSING key), `fd-uhabits` (white-window lottery,
"welcome screen once … not a firm gain", correctly kept `alive-white-window`, **not** in the 122), and `x` (signoff
"no t20 captured", window blank here).

## pair_sheet note

`pair_sheet.load_ref_board` reads this dir's `u13-ref-<board>.txt` by its `*-ref-<board>.txt` name and takes each key's
verdict **and** t20 from it (the `.txt` is self-sufficient; `--signoff` is only a fallback for keys absent from the
sheet and for flaky k/n history). This needs the master `pair_sheet.py` (`ref_board_file` / the generalized
`load_ref_board`); this lane's worktree still carries the older `u9-ref-*`-only copy, so the known answer above was run
with the master script — which is where U13 signing runs.

## Rule this round sets

A sign-off pairs against the **latest signed baseline**, assembled from that baseline's own signed runs. U13's baseline
is U12's 122-lit = the U10.1T8 116 **plus** the already-signed U12 window-4 gains and the itsdicey re-sign — not a new
judgment. Build it as an overlay: carry the unchanged tiles verbatim, and trace every moved tile to the signed run that
set it (`sources.json`). Do not reuse U10.1T8's sheet for U13: its six not-yet-lit cells would show up as false
"different".

## Boundaries

Offline; no board; nothing deployed. Inputs read read-only from the shared master checkout (`westlake-harness`) and
`westlake-harness-u7-executor`; no other worktree was modified. The 122-lit verdicts are the outer's (U10.1T8 signoff +
U12 window-4 signoff + `cb7e105ffa`); this directory only assembles them into the U13 pairing baseline.
