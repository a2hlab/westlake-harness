# Evolution retro brief — 2026-10-03 evening window (since 2026-10-02T16:00:00Z)

`evo_family.py --since 2026-10-02T16:00:00Z` (verbatim):

```
12 cards since 2026-10-02T16:00:00Z
  runtime-unverified   x1   EVO-0117  (by oc-t4)
  narrow-negative      x2   EVO-0110,EVO-0118  (by outer)
  decision             x5   EVO-0108,EVO-0109,EVO-0111,EVO-0113,EVO-0115  (by outer)
  other                x4   EVO-0107,EVO-0112,EVO-0114,EVO-0116  (by outer)
```

Harvest + retro ran per AGENTS (`OLP_EVO_REVIEW_BOARD=.octos/boards/app-lighting.md`):
harvest collected **116 cards** (the board's full history; tonight's 12 are EVO-0107..0118),
retro grouped **115 candidates**, brief at `~/.octos/outer/evo/9fb221a3dbb0df31/retro/2026-10-03T02:10:15Z-1.md`.
No FLAW records written here (outer's job).

## Families with >=2 cards tonight

**narrow-negative ×2** (EVO-0110, EVO-0116 — outer's own narrow-negative checks)
- EVO-0110: a "not present" conclusion drawn from truncated output (`find … | head -10` cut off the very file being denied).
- EVO-0116: the 09:48 "U14 already satisfies one-shard-per-key" assertion only checked lottery∩regression, not movers∩regression (13 lit M5 keys overlapped).
- **One-line tool/assertion fix**: pair every "absence" claim with a count-asserted full scan (`| wc -l` + expected count in the command, no `head`), and make the key-table disjoint check a generic all-shards assertion from the start (already done tonight: `shards pairwise disjoint` in both build_keys.py — EVO-0116's fix).

**decision ×5** (EVO-0108, EVO-0109, EVO-0111, EVO-0113, EVO-0115 — verdicts reversed on re-read)
- Pattern: predictions/readings signed before the underlying artifact was re-verified against the board's own evidence (deploy-set contents, disassembly, t5/t20 images, flaky registry).
- **One-line fix**: require each signed prediction/verdict line to cite the artifact hash it was read from (sources.json sha / commit) so re-reads are diffable, and gate "still-flippy" classifications on the flaky registry or a signed k/n before scheduling ×6 (done: lottery evidence gate in build_keys.py — EVO-0115's fix).

## Notes

- runtime-unverified ×1 (EVO-0117, oc-t4's own) — the 8-white-key ×6 misclassification; fixed by the same lottery evidence gate.
- other ×4 (EVO-0107/0112/0114/0116-class): mid-window input mutation, comment-line key extraction — both already have standing rules on the board.
