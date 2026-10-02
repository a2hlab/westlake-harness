# Stage-A T8 sweep — signed baseline (regression reference)

`outer-signoff.json` is the synthesized baseline for the stage-A T8 rerun (U10.1 bundle `190afedd3ddb`): the outer
loop's window 1-5 sign-offs merged into one per-key table, in the `benchmark/2026-10-01-u9-sweep/outer-signoff.json`
shape (per key: verdict, shard, u9, note, source windows). **Synthesis only — no new judgment**; every verdict is
carried from the signed window text.

## Counts
- **116 lit** = 115 U9-lit kept (0 regressions) + 1 firm new (`cv2-org-secuso-privacyfriendlyyahtzeedicer`, U9 was
  alive-launcher → own UI "ROLL THE DICE" = lit).
- **1 lottery**: `fd-noice` (U9 alive-white-window; lit once, white-window lottery prior 0.59 — a single lottery lit,
  not a firm gain).
- **2 not-lit/white**: `toutiao` (U9 launcher; window blank-white alive, walls 1/2 gone but short of own UI),
  `x` (U9 alive-white-window; window white).
- Flaky, counted in the 116 but flagged `lottery` (judge by k/n, a single non-lit is not a regression):
  `wikipedia` (1/3 lit, N11h white target), `cv2-de-koelle-christian-trickytripper` (2/3 lit, crash lottery).
- 119 keys total; `confirmed_regressions`: 0.

## Sources (outer-signed)
`benchmark/2026-10-02-u10-1-t8-rerun/window{1,2,3,4}-signoff/outer-signoff.json` +
`window5-signoff/outer-signoff-{gains,retests}.json`. Each key records which windows signed it.

## Use
Regression reference for later runs: a key that is `lit` here but not lit later (outside its `lottery` k/n) is a
regression signal; the two white / one lottery keys are judged by their own flakiness, not as hard controls.

## Full U9 set (166 keys)
Padded to the complete U9 sweep set (166): the 119 tested keys above + the remaining **47 U9-non-lit keys**, each
carrying its **U9 verdict** (`carried_from_u9: true`, source `window5-gains(no_change)` — the window5 gains signoff
recorded these as showing the same white/black/launcher screen as U9). No new judgment. Final counts: **116 lit**,
1 lottery (fd-noice), 2 white (toutiao, x), 31 dead, 12 alive-white-window, 2 alive-black-window, 1 alive-black-content,
1 app_failed = 166. lit unchanged at 116; the 47 carried keys are all U9-non-lit. This lets later runs diff gains
against the whole U9 surface, not just the tested subset.
