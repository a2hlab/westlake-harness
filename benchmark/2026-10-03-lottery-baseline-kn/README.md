# Lottery-key baseline k/n — how many U13 runs to judge M1 at α=0.05

Offline, no board, #80 Wikipedia line. M1 (the multi-window white of `2026-10-02-white-vs-lit` / `2026-10-02-m1-session-slots`:
the top Activity's VRI gets an empty Surface because the deployed bridge's cross-copy window lookup is a single
process-wide slot) is the mechanism of the **lottery keys wikipedia, noice, fd-noice, fd-uhabits**. This benchmark sets
the signed baseline lit-rate k/n for each, classifies each white as M1-shape or not, and computes how many U13 runs are
needed to conclude "M1 raised the lit rate."

## Headline
The lottery keys flip a coin whose **pooled baseline lit-rate is 0.25–0.58** with **very wide 95% CIs** (per-generation
n is 1–6). To call an M1 lit-rate increase at one-sided α=0.05, assuming M1 makes a key lit every time (its prediction),
run each key **noice 3 · fd-uhabits 3 · wikipedia 4 · fd-noice 6** all-lit U13 runs; judging the 4-key family jointly
(Bonferroni α=0.0125) needs **4 · 5 · 6 · 9**. A uniform **6 runs/key** clears per-key α=0.05 for all four; **9 runs/key**
clears the Bonferroni-joint bar. Fewer runs cannot distinguish M1 from the baseline lottery.

## Scope
- **Lottery set (4):** wikipedia, noice, fd-noice, fd-uhabits — white-vs-lit establishes all four are M1.
- **listmaker (cv2-com-harr1424-listmaker) EXCLUDED:** it is a stable-lit cv2 key (U9 61b lit, U10.1T8 61b lit = 2/2),
  not white/multi-window/RenderThread (LIT group in white-vs-lit; no empty_surface / RenderThread marker). M1 cannot
  raise a rate that is already 1.0, so it is not an M1-evaluation key. (`evidence/verdicts-table.txt`.)
- **U12 has NO board data:** U12 is an offline bundle assembly (bf6c0fb6, `execution_enabled=false`, `board_writes=0`),
  so the requested "U12 stage-A windows 1-4" produced **no t20 runs** for any key. The U13 window itself is the first
  post-U10.1T8 board data for these keys.
- **U9 is a single signed sweep run per key** (not a zero-variable repeat series; no u9-flaky-repeat benchmark exists).
- **U8 repeat hilogs are PURGED** (files_gone; only t20.jpeg): k/n usable, but those whites **cannot be confirmed M1**.

## Baseline k/n per key per generation (outer-signed t20; Wilson 95% CI) — `evidence/kn-output.txt`
| key | U5 | U7 | U8 | U9 | U10.1T8 | pooled p0 (95% CI) |
|---|---|---|---|---|---|---|
| wikipedia | — | 0/1 | 3/6 | 1/1 | 1/3 | **5/11 = 0.45 [0.21, 0.72]** |
| noice | — | 1/2 | — | 0/1 | 0/1 | **1/4 = 0.25 [0.05, 0.70]** |
| fd-noice | 2/3 | 1/1 | 3/6 | 0/1 | 1/1 | **7/12 = 0.58 [0.32, 0.81]** |
| fd-uhabits | 1/3 | 1/1 | 2/5¹ | 0/1 | 0/1 | **4/11 = 0.36 [0.15, 0.65]** |

¹ fd-uhabits U8: one of 6 attempts (r2) was void (killed by a tool timeout), excluded → 2/5.
Every per-generation CI spans ≥0.5 in width (n=1–6) — no single generation pins the rate. The rate is also **not stable
across generations**: U5/U7 skew lit, the recent U9+U10.1T8 skew white (wikipedia 2/4, fd-noice 1/2, noice 0/2,
fd-uhabits 0/2). The pooled p0 is the best estimate of the common "lottery coin" (M1 is the same single-slot defect in
every generation), used below; the recent-state skew is a caveat, not a different mechanism.

## M1-shape of each white (`evidence/m1-shape.txt`)
white-vs-lit classified **11/11 paired runs correctly** (white 7/7 misroute True, lit 4/4 False) and the U10.1T8
population (M1 white = noice, fd-uhabits; misroute 0/117 among lit). So every classifiable white of these four keys is
**M1** (top Activity's VRI empty, published first). U8 whites are **unknown** (hilog gone). The static root: deployed
bridge `84695d62`'s cross-copy window lookup is a single process-wide slot overwritten by every createSession
(`oh_window_manager_client.cpp:96-128`); the first-created (top) Activity loses the race → white.

## How many U13 runs to judge "M1 raised the lit rate" at α=0.05 — `kn_stats.py`
M1's prediction (`m1-session-slots/predictions.csv`): noice/fd-uhabits white→lit, wikipedia/fd-noice lottery→stable-high;
i.e. under M1 the key is lit essentially every run (p1≈1.0). Then observing **n consecutive lit** U13 runs rejects
H0: rate = p0 (the baseline lottery) at one-sided α when `p0^n ≤ α` (exact binomial):

| key | pooled p0 | n @ α=0.05 | n @ Bonferroni α=0.0125 (4-key joint) | two-proportion n/side (partial effect, p1=0.99, power 0.8) |
|---|---|---|---|---|
| noice | 0.25 | **3** | 4 | 5 |
| fd-uhabits | 0.36 | **3** | 5 | 6 |
| wikipedia | 0.45 | **4** | 6 | 8 |
| fd-noice | 0.58 | **6** | 9 | 12 |

**Recommendation.** Run each lottery key **6 times** in the U13 window → clears per-key α=0.05 for all four (fd-noice is
the binding constraint at 6). If the outer wants to control family-wise error over the 4 keys jointly, run **9 times**
each (fd-noice at Bonferroni 0.0125). These assume M1 fully converts the key to lit; if M1 only *shifts the odds*
(partial), the two-proportion column (8–12/key) is the budget to detect it with 80% power. Pair the t20 with a
`multiwin.py` readback each run — "lit AND misroute False every run" is M1's acceptance signal (`predictions.csv`), so a
white that is **not** M1 (misroute False) would be a different wall and must not be counted against M1.

## This round's rule
A "lottery" verdict is a Bernoulli rate, not a fact: report it as k/n with a Wilson CI and never from a single run. The
baseline here is too thin per-generation (n=1–6) to judge M1 from one or two U13 runs — the sample-size table is the
deliverable. Pool across generations only because M1 is the same single-slot defect in all of them, and say so. Confirm
each U13 lit with the M1 detector (misroute False), so an unrelated white is not scored as an M1 failure. Exclude keys
that are already stable-lit (listmaker) — there is no rate for M1 to raise.

## Files
- `baselines.csv` — the signed k/n per (key, generation). `kn_stats.py` → `evidence/kn-output.txt` (Wilson CI, pooled p0,
  min-n, two-proportion).
- `evidence/verdicts-table.txt` — every signed t20 run with source + hilog availability; listmaker exclusion; what's not available.
- `evidence/m1-shape.txt` — per-white M1 classification (via white-vs-lit multiwin) + the static root.
