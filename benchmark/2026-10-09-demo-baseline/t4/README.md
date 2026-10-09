# Accelerated demo stability: grouping delivery

## Evidence first

**A reference board is not a second candidate run.** U14 signoffs frequently
carry `reference_board`; counting it would invent cross-board stability. This
generator only counts the actual `board` of the signed candidate observation.
It reads the nine canonical U13 windows 1–4 and U14 windows 1–5 signoffs, then
binds measured counts to their pair-sheet candidate `record.json` files.
Unsigned runners, reference/control pictures and duplicate signoff copies do not
add runs. Pair-sheet automatic similarity is never used as a lighting verdict.

`groups.json` mechanically partitions the 128 selected packages. Every stable
entry has >=2 confirmed lit candidate runs on >=2 actual boards, no signed white
observation, and no empty/error/game override. Confirmed historical nonlit is
conservatively edge as well. All source JSON hashes/pointers, record hashes and
per-source counts are retained. `noice` 2.5.1 cannot boost selected `fd-noice`
2.5.7: distinct APK identities are not interchangeable.

The three incomplete history bindings are explicit: two old Noice-version rows
and one U13 Minesweeper row without an associated candidate screenshot/record.
They supply no positive evidence. Minesweeper is a mandatory game and remains
edge regardless. OrganicMaps' signed U14 window-5 unresolved-white already forces
edge; unsigned window-6 runner observations are not counted as lit.

## Runner-facing fields

- `stable_keys` / `edge_keys` and `apps[].group` are the partition.
- `apps[].screenshot_seconds` is superseded by `shot-tiers.json`: capture delay
  follows historical same-PID child-to-first-frame maximum, not group membership.
- `special_slots`: Toutiao and BoatAttack are edge, pending their own input and
  acceptance work; these two reserved slots do not inflate the 128-package count.
- Latest t4 decision uses **61b t3 round 1 + post-reboot round 3**. Spare-board
  edge k/n is separate prescreen evidence, never acceptance on 61b. No runner is
  started by this generator and `execution_enabled=false` throughout.
- This is historic scheduling evidence, not fresh content or interaction signoff.
  The 32 empty screens remain optional, not part of the critical-path 94-content
  baseline under the latest user decision. No guessed click is executed.

## Reproduce

```sh
python3 benchmark/2026-10-09-demo-baseline/t4/build_groups.py
python3 benchmark/2026-10-09-demo-baseline/t4/build_groups.py \
  --out benchmark/2026-10-09-demo-baseline/t4/.artifacts/groups-second.json
cmp benchmark/2026-10-09-demo-baseline/t4/groups.json \
  benchmark/2026-10-09-demo-baseline/t4/.artifacts/groups-second.json
python3 benchmark/2026-10-09-demo-baseline/t4/test_groups.py
```

Outputs contain no timestamps and use sorted source/key traversal. The second
generation is byte-identical; hashes, exits and raw stdout/stderr are retained
in `group-validation.json` and `evidence/`. Changes stay in the lane worktree for
outer landing because Git worktree metadata is read-only. No board/VM/SSH access,
no lock, no promotion and no gate-table modification occurs.

This delivery prioritizes grouping for cx-t0. The stability summarizer is being
adapted to the newly accelerated/spare-prescreen policy; the superseded four-round
prototype is not part of this landing.
