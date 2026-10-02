# U13 stage-A observation key-table — input for cx-t0's board plan

Offline, #80/#90. The **key-table input** for cx-t0's U13 stage-A observation plan: which keys run on which board, how
many times, in what priority, split into ≤45-min windows. This is an INPUT (keys + counts + priority + window split),
not a full board_run plan — cx-t0 fills the U13 deploy params (bundle/runtime/boot restore SHAs, smoke spec, regression
gate). `u13-stage-a-keys.json` is the machine-readable table; `keys/<board>/*.txt` are the new shard lists; the 116-lit
set is referenced from the U12 assembly (priority unchanged).

## Design (per board, priority order)
Every key stays on its **U12 board** (no re-imaging; inputs already staged at `~/a2hlab/app-inputs`). Each board runs
four shards, highest-information first:
1. **movers** (priority 1): the U13 predicted first-fatal movers on that board — run first (densest signal).
2. **cv2-new** (priority 2): the never-run-signed cv2 java-walls fixes.
3. **lottery** (priority 3): the M1 lottery keys, each **×6 consecutive on one board** (no cross-board mixing, so k/n is
   a clean Bernoulli sequence) + a **multiwin misroute check per run**.
4. **lit-regression** (priority 4): the U12 116-lit set, ×1, to confirm no regression under U13 — lowest priority, fills
   the remaining window time.

## Shards and counts
| board | movers | cv2-new | lottery (×6) | lit-reg | runs | ~min @1.75/run | windows |
|---|---|---|---|---|---|---|---|
| 5ea | 5 | 1 | fd-uhabits, fd-noice (12) | 37 | 55 | 96 | 3 |
| 5cd | 5 | 0 | wikipedia (6) | 37¹ | 48 | 84 | 3 |
| 61b | 4 | 3 | noice (6) | 41 | 54 | 95 | 3 |

¹ 5cd lit-regression excludes `wikipedia` — it is measured ×6 in the lottery shard (that ×6 also serves as its
regression run). Totals: **157 runs, ~137 unique keys, 9 windows** (3/board). Lottery = 24 runs (4 keys × 6).

### ① lit set (116 + fd-client), 3-board sharding, priority = U12
Referenced from `u12-assembly/keys/<board>/{lit-original,lit-cv2}.txt` (5ea 37, 5cd 38→37, 61b 41 = 116). Priority
unchanged from U12. `fd-client` is NOT lit — it is a predicted-mover (java-walls R1), placed in 5cd `movers`.

### ② lottery keys × 6 (`keys/<board>/lottery.txt`, `runs_per_key: 6`, `multiwin_check: true`)
Each of the 4 lottery keys runs **6 consecutive times on a single board** (fd-uhabits+fd-noice→5ea, wikipedia→5cd,
noice→61b). Per the baseline (`2026-10-03-lottery-baseline-kn`), 6 runs/key clears per-key α=0.05 (fd-noice is the
binding constraint at 6). **Each run must record the multiwin misroute flag** (`benchmark/2026-10-02-white-vs-lit/multiwin.py`
on the run's hilog): `lit AND misroute=False` is the M1-fixed acceptance; a white that is `misroute=False` is a different
wall and is not scored against M1. noice/fd-uhabits/wikipedia/fd-noice are therefore NOT duplicated in `movers` — the
lottery ×6 IS their M1 measurement.

### ③ predicted-movers (first-priority shard, `keys/<board>/movers.txt`)
GetLongField 7 (= my fix covers all 7: `glmark2`, `localsend`, `fd-fluffychat`, `fd-immich` + the 3 Flutter `fd-saber`,
`fd-kitchenowl`, `fd-libre` that ride the same `AAssetManager_fromJava` lazy-init, `2026-10-02-u13-flutter-abort-3`)
+ `vlc` + `chessclock` (cv2) + `mcdonalds` + `privacybrowser` (cv2) + `x` + `fd-api` + `fd-client`. Placed on each key's
U12 board: 5ea {localsend, fd-kitchenowl, vlc, privacybrowser, fd-api}; 5cd {fd-fluffychat, fd-immich, fd-libre,
chessclock, fd-client}; 61b {glmark2, fd-saber, mcdonalds, x}. The M1 movers (noice, fd-uhabits) are in ② (×6).

### ④ never-run cv2 keys (`keys/<board>/cv2-new.txt`)
`notepad`, `clipboardeditor`, `packlist`, `moodcairns` — the java-walls R1/R2/R3/S1/S2 fixes, never run in a signed
window. On their U12 boards: 5ea {clipboardeditor}; 61b {notepad, packlist, moodcairns}.

### ⑤ per-board time + window split
Per-run wall ≈ **1.75 min** (signed t20 shot lands ~22 s; the variable is `--reinstall` + launch + teardown). With
`stop_new_tests_by_minute=35`, ~**20 runs/window** start, finishing within the 45-min cap. So **3 windows/board** (9
total): window 1 = movers + cv2-new + lottery (the U13 signal); windows 2–3 = lit-regression. At a faster 1.5 min/run
(~23/window) 5cd could fit 2 windows; cx-t0 should size from the first window's measured rate (the DIGEST rule: let the
board, not the estimate, set the cadence).

## Boundaries / notes for cx-t0
- This is a **key-table input**, not a deploy plan: U13 bundle/runtime/boot restore SHAs, smoke spec, regression gate,
  and the exact `board_run` JSON are cx-t0's to fill (same structure as `u12-assembly/plan-<board>.json`).
- `batch_flags_base` = `--reinstall --hilog 20 --shots 5,20 --focus-check` (U12's). The lottery shard needs the hilog
  (for multiwin) — already included.
- Keep each lottery key's 6 runs on ONE board and consecutive; do not interleave boards (k/n must be one Bernoulli
  sequence per key). Count captures from `facts.txt`, not the plan (AGENTS #63/#71).
- No board action here — cx-t0 runs the windows after the U13 unified state + outer approval.

## Files
- `u13-stage-a-keys.json` — the per-board shard table (counts, priority, window split, multiwin-check, U12 lit refs).
- `keys/{5ea,5cd,61b}/{movers,cv2-new,lottery}.txt` — the new shard key lists.
- `evidence/placement.txt` — each predicted-mover/lottery key's U12 board + shard (the source of the board assignment).
