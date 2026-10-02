# U10.1T8 reference set: pair the U12 window against U10.1T8, not U9

The U12 sign-off compares each U12 window t20 with the signed U10.1T8 baseline
(`../outer-signoff.json`, 166 keys, 116 lit). The two baselines differ:

- U9 was the old reference: `benchmark/2026-10-02-u10-1-t8-rerun/u9-reference` + the U9 signoff.
- U10.1T8 gained `cv2-org-secuso-privacyfriendlyyahtzeedicer`. U9 had it as alive-launcher; U10.1T8 has it lit.
- U10.1T8 re-read flaky keys from retests: trickytripper and wikipedia are lit from their window-5 r1.

Against U9, a U12 window would flag these as "different" every time. This directory is the same per-board format as
`u9-reference`, built from U10.1T8's own signed runs.

## What is here

**Per board:**
- `u10-1-t8-ref-{5ea,5cd,61b}.txt` (55 / 55 / 56 keys = 166). One line per cell:
  `row R col C  <key>  verdict=<U10.1T8 signed>  corpus=<original|cv2>  <real t20 path or MISSING>`.
  - Row/col match the jpeg grid.
  - Key order = the U12 plan's shard concatenation, `benchmark/2026-10-02-u12-assembly/plan-<board>.json`: lit-original,
    lit-cv2, unlit-original, unlit-cv2.
  - The keys files named in the plans are byte-identical to the landed `keys/` copies; the build checks this.
- `u10-1-t8-ref-<board>.jpeg`: `contact_sheet.sh --cols 7`, unlabelled tiles (no drawtext); read the cell from the
  txt.

**Shared files:**
- `sources.json`: per key, its signing windows, which run was picked and why, the run board/shard, and the t20 path
  and sha256.
- `build_reference.py`: regenerates everything from the signoff, the plans and the real runs.
- `known-answers/`: `pair_sheet` output for each window's real run against this reference.

**Verdict tallies (= the signoff):**

| board | keys | lit | other verdicts | missing t20 |
|---|---|---|---|---|
| 5ea | 55 | 37 | lottery 1 (fd-noice), dead 13, alive-white-window 1, alive-black-content 1, app_failed 1, alive-black-window 1 | 1 |
| 5cd | 55 | 38 | alive-white-window 8, dead 9 | 0 |
| 61b | 56 | 41 | white 2 (toutiao, x), dead 9, alive-white-window 3, alive-black-window 1 | 0 |

Lit 37 + 38 + 41 = 116, the signed count. The one missing t20 is `cv2-com-frequent-habits` (app_failed): its window-5
run has no t20, the same as U9.

## Which t20 (no judgment, no substitution)

Each key's `windows` field lists its signing windows. The window-to-run mapping:

| signing window | run directory (`$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/`) |
|---|---|
| window1 | `window/` |
| window2, window3, window4 | `window2/`, `window3/`, `window4/` |
| window5-gains, window5-gains(no_change), window5-retests | `window5/` |

Records are walked with `pair_sheet.discover`, the same walk `pair_sheet --run` does.

**Rules:**
1. **The last listed window signs.** An earlier one is listed first when it had no t20 or was outvoted by a retest:
   - fd-reader: w1 interrupted, then w5 reader-retest;
   - toutiao: w1 install failed, then w5 toutiao-gain;
   - wikipedia: w1 white, then w5 retests;
   - trickytripper: w3 launcher, then w5 retests.
2. **Several runs in that window** (window5 `*-retest-1/-2`): take the first attempt whose signed text equals the verdict.
   The text is in `window5-signoff/outer-signoff-retests.json` `attempts`, `"w5 rN: lit"` → shard `*-retest-N`.
   - trickytripper → retest-1 (lit);
   - wikipedia → retest-1 (lit; r2 was white).
3. **The signing window has no record of the key**: take the window its signed text names.
   - One case: `fd-binaryeye` is signed in window4 as "same screen as U9 (window 2 t20)" and has no window4 record, so
     its t20 is window2's.
   - Nothing else is borrowed. A record without `t20.jpeg` is `MISSING`.

**Picks:** window3 76, window5 52, window1 19, window2 11 + 1 (fd-binaryeye), window4 5, window5 retest-1 2.

## pair_sheet change (`scripts/lab/pair_sheet.py`, small)

`load_ref_board` used to read only `u9-ref-<board>.txt`. It now:
- reads `u9-ref-<board>.txt` if present;
- otherwise reads the single `<label>-ref-<board>.txt` in the same line format;
- **refuses** (exits) when a directory has two listings for one board.

The output fields keep their names (`u9_verdict`, `u9_t20`, the U9 tile label). With this reference they mean "the
U10.1T8 reference". Defaults are unchanged: `--reference`/`--signoff` still point at U9, so window 1-5 re-reads are
untouched. The U12 window passes:

```
pair_sheet.py --run <U12 window> --reference benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference \
              --signoff benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json
```

**Tests:** `scripts/lab/tests/test_pair_sheet.py` adds 5 (23 in total, all pass; `--selftest` still 77/0):
- legacy name, labelled name, two listings refused;
- the two known answers below, skipped when the real runs are absent.

## Known answers (real window runs vs this reference; `known-answers/`)

| window | pairs | same | different | no-window | no-ref | non-same keys, and why it is right |
|---|---|---|---|---|---|---|
| window3 | 77 | 76 | 1 | 0 | **0** | trickytripper sim 0.5: w3 launcher (RenderThread SIGSEGV) vs its signed lit w5 r1, the known difference |
| window5 | 56 | 54 | 0 | 2 | 0 | wikipedia retest-2 (signed white in r2, flaky 1/3); frequent-habits (app_failed, no t20 on either side) |
| window1 | 22 | 19 | 0 | 3 | 0 | fd-reader (w1 interrupted, no t20), wikipedia (w1 white), toutiao (w1 install failed): all as signed |
| window2 | 12 | 12 | 0 | 0 | 0 | |
| window4 | 5 | 5 | 0 | 0 | 0 | |

- **yahtzeedicer in window5:** `U9=lit auto=same sim=1.0` against this reference. Against U9 it is
  `U9=alive-launcher-foreground auto=different sim=0.387`.
- **window5 as a whole:** 54 same / 0 different against this reference, vs 49 / 3 against U9.

## Rule this round sets

A sign-off pairs against the **latest signed baseline**, built from that baseline's own signing runs:
- every reference t20 is traced to the run that carried the verdict (`sources.json`);
- a pointer in the signed text ("window 2 t20") is followed; nothing else is borrowed from another run.

When a new baseline is signed (U12), build its reference the same way and pass it with `--reference`/`--signoff`. Do
not reuse an older baseline's sheet: its gains and lottery re-reads show up as false "different".
