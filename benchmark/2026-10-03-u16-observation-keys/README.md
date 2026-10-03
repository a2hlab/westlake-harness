# U16 stage-A observation keys (input for cx-t0, not a deployment plan)

Built by `build_keys.py`. **Reference is a PLACEHOLDER**: built against the U14 reference
(126 lit); after U15 sign-off + U16 assembly, swap `REF` to the U16 reference and rebuild
(`reference_note` in the json says the same).

## Board load

| Board | runs | movers | risk-watch (×1) | theme-watch (×1) | white-watch (×1) | lottery (×6) | lit-regression | ~min | windows (≤25 runs / 45 min) |
|---|---|---|---|---|---|---|---|---|---|
| 5ea | 49 | 3 | 1 | 1 | 0 | 1 key (6 runs) | 38 | 85.8 | 2 |
| 5cd | 52 | 5 | 1 | 1 | 4 | 1 key (6 runs) | 35 | 91.0 | 3 |
| 61b | 52 | 1 | 2 | 4 | 2 | 1 key (6 runs) | 37 | 91.0 | 3 |

## Shards

- **movers (9, priority 1)** — U16 fix observation points, per-key source+expectation in the json:
  - `u16 t1` — fd-wifianalyzer (5cd): WifiManager 8 methods no-wifi semantics (stubs 85938130); first fatal moves past the NoSuchMethodError (cluster N).
  - `u16 t3` — fd-breezyweather (5cd): launch-transaction ON_START sync (**runtime JAR f6f5face**, benchmark/2026-10-03-u16-t3-build/); first fatal moves past weatherView lateinit.
  - `u16 flutter interposer (NEW in U16)` — localsend, fd-kitchenowl (5ea); fd-fluffychat, fd-libre (5cd): **SHA pending** (cc-t3 building; benchmark/2026-10-03-u16-flutter-impeller-proc/); first fatal expected to move past pc=0 glDepthRange.
  - `u16 t4 M1-split replay evidence (FZ-009 pre-registration)` — fd-uhabits (5ea), wikipedia (5cd), noice (61b): **runtime native 1d42dbfb** (benchmark/2026-10-03-u16-t4-m1-runtime/); [M1-COPY] semantics unchanged, auto=same expected. These leave lottery/lit-regression (one shard per key).
- **risk-watch (4, priority 2)** — t3's native-engine lit keys fd-mpv (5ea), fd-minetest (5cd), fd-organicmaps + fd-stk (61b): SurfaceView/GL re-verify for onStart-at-launch; ×1 doubles as their regression run (out of lit-regression).
- **theme-watch (priority 3)** — U15 watchlist still standing (lit keys only; overlaps with movers/lottery stay there).
- **white-watch (priority 4)** — unevidenced white-window keys (5cd ×4, 61b ×2).
- **lottery (priority 5)** — flaky-only gate, now also excluding movers/risk-watch: 5ea fd-noice; 5cd fd-notes; 61b antennapod (×6 consecutive, doubles as regression). fd-uhabits/wikipedia/noice moved to movers as t4 replay evidence.
- **lit-regression (priority 6)** — reference lit minus every key covered above.

## Known answers (asserted at build time)

- shards pairwise disjoint per board; lit-regression(110) ∪ lit risk-watch(4) ∪ lit theme-watch(6) ∪ lit lottery(3) ∪ lit movers(3) == reference 126 lit keys; boards match; lottery all evidenced.
- **every SHA prefix quoted in a mover source exists in that source's deliverable dir** (asserted at build; explicitly-pending deliverables — the flutter interposer — carry no SHA yet).

## fix-observers status

`check_fix_observers.py` against a U16 increments list: **not yet possible — no U16-on-U15
increments.csv exists on master at build time** (searched; only U14-on-U13 and U15-on-U14).
To re-run when cx-bms's draft lands:

    python3 scripts/lab/check_fix_observers.py <u16 increments.csv> \
        benchmark/2026-10-03-u16-observation-keys/u16-stage-a-keys.json --csv <out>.csv

Expected coverage: movers' source strings name t1's stubs SHA (85938130), t3's runtime SHA
(1d42dbfb) and the flutter interposer; the M1 replay movers cover the t4 runtime split via
the same SHA; risk-watch/theme-watch rows cover the lit keys they name.
