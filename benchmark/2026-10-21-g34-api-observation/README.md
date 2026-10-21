# G35: append the G34 locale ABI trial as API observation 64

## What was wrong before

Observation 63 recorded the G30 locale ABI candidate as offline only. The outer loop then ran it once on
5ea (G34). Without a new row the table could not show the actual trial outcome. The game still failed,
and the device was restored.

## What this adds

One row, `OBS-20261021-G34-LOCALE-TRIAL`, after the strict 63-row prefix of master `86b9fdb160`
(`observations.json` `8fb15e28…`). The 315 atlas, the renderer `render.py` (`0276c50e…`) and all prior README
lines are unchanged. All inputs come from master `1a3b38755e`. The 104 references are derived from:

- each G34 package's own `landing-paths.txt` (closed 51, launch addendum 14, static prediction 11);
- the ten `admission-01` files;
- the execution and postclose archive receipts and three outer-review records;
- four G30 source and four G30 build files, linked rather than copied.

All 104 equal their bytes at `1a3b38755e` ([input-pins.json](input-pins.json)).

| Fact | Value | Source |
|---|---|---|
| Apply / rollback | U7 active_verified rc0 (36 ops) / rolled_back rc0 (36 ops) | closed/results.json |
| UI attempts | first: remote layout directory missing, no click; second: one icon click | closed/receipts/game-ui/failure.json, results.json |
| Outcome | white then launcher; parent reports child 29761 signal11 at 23:22:11.437 (L3791); no game frame | closed, images.json, g34-launch-addendum |
| Locale | the earlier relocation error is not seen; this run got further, which is not a general API pass | closed, addendum |
| Unknown | fault PC, faulting TID, stack, cause, provider winner | closed, addendum, postclose-observations |
| Dfx | in-window `-x`+`-z` body CODE:-31 (rc0); later tag query empty; 25 s full buffer ends 23:17:38; a later full query (rc0) covers 23:22 but recovers no stack. None proves there is no crash record | closed, postclose-observations, outer-review |
| Restoration | 319/319 hashes, 61 mount stacks, Boat3, control images, power SLEEP/30000/10000, unlock rc0; 318 exceptions retired | closed/results.json, admission-retirement.json |
| Cleanup | two force-stop bodies 10106401 (rc0): not successful stops; later ps shows test UIDs absent | outer-review/closure-force-stop-correction.json |
| Static | 433 strong imports with a named provider, 0 new fix keys, winner UNKNOWN | g34-static-prediction |
| Archive | closed `remote-archive-pending.json` kept as packaging-time snapshot; execution `d80d2025…` and postclose `2441351e…` remotely verified later | closed, execution-archive, postclose-observations |

The candidate is not deployed and not frozen. Only one app is involved, so the two-app freeze condition
is not met, and nothing is playable.

## Checks

`check_observation.py` reuses the G33 checker, which now requires the 63-row prefix and accepts later
rows. Its G30 semantics, including the archive-snapshot positive case, are unchanged. A 64th row is a
positive check, and truncation below 63 or a later row with a missing reference is refused. On top of
that, G35 requires:

- exactly 64 rows; row 64 equals [added-row.json](added-row.json);
- references equal to the landing-derived set recomputed by `make_row.build_row`, each verified by SHA and bytes;
- semantic guards for every limit above;
- cross-checks of the closed, retirement, UI-failure, force-stop correction, addendum, static, both archive,
  postclose, image and G30 receipts.

The closed package's pending receipt is required to stay pending. The verified sidecars are required to
stay verified. They coexist, and neither invalidates the other.

The G15, G17, G25, G29, G31 and G33 checks run first, including original-renderer byte equality of
`index.html`, `observations.csv` and `results.json`. 20 negative cases are refused for the expected reason:

- history drift and a G30 row freeze claim;
- truncation to 63, a 65th row, a row 64 edit, dropped evidence, an omitted landing path, a missing
  reference and SHA drift;
- HTML-only and CSV-only false success;
- false success in the table, a game frame inferred from screenshot count, current deployment and freeze;
- a known root cause, locale absence as a general API pass, and Dfx CODE:-31 read as an empty result;
- an rc0 force-stop counted as success, and the historical pending statement rewritten as an error.

Actual run:

- [check.stdout.txt](check.stdout.txt), [check.stderr.txt](check.stderr.txt) (empty), [check.rc](check.rc) (0);
- Rust targets for G15/G17/G25/G29/G31/G33/G35 in [rust-tests.txt](rust-tests.txt) (7 passed).

## Rule set here

A device trial row cites each evidence package's own landing list as a whole. The checker recomputes that
set, so references cannot be silently dropped or added. Outer rc0 is never read as inner success: Dfx and
force-stop body errors stay visible. A packaging-time "pending" and a later "verified" receipt are both
history. The later one is added as a sidecar and does not rewrite the earlier one.

No device, REA, VM, runtime build, G14/T38 or push.
