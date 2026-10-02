# N11h white-rate prior (judgment baseline)

N11h targets the **white-lottery** keys, so a single lit/white in the window proves nothing. This gives each key's
historical **white rate** as a prior, and the **"lit k/n to count as an effective improvement"** criterion. Offline,
read-only. Verdicts are the outer loop's — this lane never self-judges lit from a screenshot.

## Method
- **Signed lit/white** come only from outer sign-off JSONs: U8 (`e953c0921536`), U9 (`a8cb9a5a45a6`), cv2/U7
  (`68b7fb016253`), and the T8 Stage-A window1 sign-off (one verdict per key per source). Normalized:
  lit/lit-webview-fallback -> **lit**; alive-white-window/alive-blank-window -> **white**; dead/app_failed -> dead;
  rest -> other.
- **Zero-variable repeat rates** (the real lottery measurement) come from `knowledge/gates/flaky-keys.json`
  (outer-read), curated per key with the lit/white/crash split.
- **`run_index.py` index** (`$WORKSPACES/westlake-inputs/run-index/index.jsonl`, 3929 rows) gives `n_runs_index`
  and `alive_t20` per key — **process-alive context only; the index does not judge lit/white** (by design). Unsigned
  runs are therefore `unknown` for white-rate and are not counted as lit or white.
- **white_rate = white / (lit + white)** over the signed + repeat observations (dead/other excluded — a dead run is a
  different wall, not a white-lottery outcome). 95% CI = Wilson.

## white vs crash — not every "flaky" key is a white lottery
The flaky registry has 7 keys; they split by **what the non-lit outcome is**:
- **WHITE lottery (lit vs blank-white window) = N11h's target**: `fd-noice`, `fd-uhabits`, `noice`, `wikipedia`
  (the "two-Activity / COMPOSE-WALL window-creation race"). N11h single-copy is the proposed fix.
- **CRASH lottery (lit vs RenderThread SIGSEGV/cppcrash) = NOT a white lottery**: `antennapod`, `fd-notes`, `zigzag`.
  Their white_rate is ~0; N11h's white fix does not address a render-thread crash. Included here for completeness per
  the dispatch, flagged out of N11h white scope.

## Table (full data in white-rate-prior.csv)
| key | type | n_idx | lit_obs | white_obs | white_rate [95% CI] | req lit-streak @.05 / @.10 |
|---|---|---|---|---|---|---|
| **fd-noice** | WHITE | 114 | 7 | 10 | **0.59** [0.36,0.78] | **4 / 3** |
| **fd-uhabits** | WHITE | 51 | 3 | 7 | **0.70** [0.40,0.89] | **3 / 2** |
| **noice** | WHITE | 58 | 2 | 2 | **0.50** [0.15,0.85] | **5 / 4** |
| **wikipedia** | WHITE | 97 | 5 | 4 | **0.44** [0.19,0.73] | **6 / 4** |
| cv2-org-andresoviedo-dddmodel2 | consistent-white | 9 | 0 | 3 | 1.00 [0.44,1.00] | 1 / 1 |
| cv2-com-bytehamster-flowitgame | consistent-white | 8 | 0 | 1 | 1.00 [0.21,1.00] | 1 / 1 |
| cv2-com-degeder-yam | consistent-white | 14 | 0 | 1 | 1.00 [0.21,1.00] | 1 / 1 |
| fd-AppManager | consistent-white | 53 | 0 | 2 | 1.00 [0.34,1.00] | 1 / 1 |
| fd-app | consistent-white | 41 | 0 | 2 | 1.00 [0.34,1.00] | 1 / 1 |
| termux | consistent-white | 44 | 0 | 2 | 1.00 [0.34,1.00] | 1 / 1 |
| x | consistent-white | 40 | 0 | 1 | 1.00 [0.21,1.00] | 1 / 1 |
| cv2-dev-obfusk-jiten-webview | consistent-white | 7 | 0 | 1 | 1.00 [0.21,1.00] | 1 / 1 |
| fd-shatteredpixeldungeon | consistent-white | 41 | 0 | 2 | 1.00 [0.34,1.00] | 1 / 1 |
| cv2-ca-vaults-randomlydie | mixed (flips) | 12 | 1 | 1 | 0.50 [0.09,0.91] | 5 / 4 |
| cv2-com-paultirk-yatoo | mixed (flips) | 12 | 1 | 1 | 0.50 [0.09,0.91] | 5 / 4 |
| fd-k9 | consistent-lit (control) | 53 | 3 | 0 | 0.00 [0.00,0.56] | — |
| fd-com-amaze-filemanager | consistent-lit (control) | 45 | 3 | 0 | 0.00 [0.00,0.56] | — |
| fd-libretube | consistent-lit (control) | 41 | 3 | 0 | 0.00 [0.00,0.56] | — |
| antennapod | CRASH (not white) | 89 | 10 | 0 | 0.00 [0.00,0.28] | — |
| fd-notes | CRASH (not white) | 39 | 6 | 0 | 0.00 [0.00,0.39] | — |
| zigzag | CRASH (not white) | 169 | 1 | 0 | 0.00 [0.00,0.79] | — |

## Criterion — "lit k/n to count as effective improvement"
Null hypothesis = N11h changed nothing; the key keeps white-lotterying at its prior rate `p_white` (so lit at
`p_lit = 1 - p_white`). Observing an **all-lit streak of n** has null probability `p_lit^n`. Reject the null (claim
improvement) when `p_lit^n <= alpha`:

> **n = ceil( ln(alpha) / ln(1 - p_white) )**, all n launches must be lit.

Per prior white rate (point estimate), at alpha=0.05:
- p_white 0.44 (wikipedia) -> **6/6**; 0.50 (noice) -> **5/5**; 0.59 (fd-noice) -> **4/4**; 0.70 (fd-uhabits) -> **3/3**.
- (The dispatch's "50% -> 3/3" example corresponds to alpha≈0.125; the table's @.10 column is the looser bar.)
- consistent-white (p_white≈1.0): a **single** lit already rejects "stays white" (n=1) — but only if the baseline is
  truly deterministic-white; with n<3 signed obs, first run a short baseline repeat to rule out an unmeasured lottery
  **or** an unfixable other-wall (a consistent-white key may be white for a wall N11h doesn't touch, in which case it
  stays white and that is NOT an N11h failure).
- consistent-lit controls (fd-k9, amaze, libretube): no streak — they must simply **stay lit**; a single dead/white
  is a regression signal.
- CRASH keys (antennapod, fd-notes, zigzag): outside N11h's white scope — judge by crash-vs-lit, not by this table.

**Operational consequence for the N11h window:** one launch per key is **insufficient** for the four white-lottery
targets. The window must **relaunch each of fd-noice / fd-uhabits / noice / wikipedia** enough times to meet its
streak (3-6 each) — a single lit there could be lottery luck. Budget the ≤30min window accordingly (repeat the 4
white targets; one launch suffices for the consistent-white/consistent-lit keys).

## Honest caveats
- **Signed lit/white data is thin** (mostly 1 obs per key per gen; the 4 white-lottery keys have the only multi-run
  repeats). The point-estimate white rates have wide CIs — treat `req lit-streak` as a **minimum**. For a conservative
  bar, use the **lower** CI bound of white_rate (higher p_lit) -> larger n (e.g. wikipedia lower CI 0.19 -> n≈15),
  i.e. the thinner the prior, the more the window should also gather fresh baseline repeats.
- `white` is counted only from outer-signed/outer-read observations; unsigned index runs (the bulk of `n_idx`) are
  `unknown`, never silently scored lit/white.
- `cv2-*` keys' signed source is the cv2/U7 sweep + U8/U9 where present; several are 1-2 obs only.

## Sources
- `knowledge/gates/flaky-keys.json`; `benchmark/2026-10-01-{u8-sweep,u9-sweep,cv2-sweep}/outer-signoff.json`;
  `benchmark/2026-10-02-u10-1-t8-rerun/window1-signoff/outer-signoff.json`;
  `$WORKSPACES/westlake-inputs/run-index/index.jsonl` (run_index.py, oc-t4 rebuilt 2026-10-02).
