# G31: append the G28 native-route trial as API observation 62

## What was wrong before

Observation 61 recorded the G26 native-route candidate as built offline and not deployed. The outer loop
then ran it once on 5ea (G28). Without a new row the table would still say "no runtime evidence" for that
candidate, and a reader could not find the real result: the game failed, and the device was restored.

## What this adds

One row, `OBS-20261021-G28-NATIVE-ROUTE-TRIAL`, after the strict 61-row prefix of master `782b588de8`
(`observations.json` `d63833ad…`). The 315 atlas, the renderer `render.py` (`0276c50e…`) and all prior README
lines are unchanged. All G28 references come from master `78ea979419`, which only adds
`native-route-window/closed/remote-archive.json` and changes one README line versus `df65e3f5be`
(see [input-pins.json](input-pins.json)).

| Fact | Value | Source |
|---|---|---|
| Apply / rollback | U7 rc0 / rc0 | closed/results.json |
| Launch | one ordinary icon click; child 14857 white, then launcher; exit code 1 | closed, addendum |
| Game frames | none observed | closed, images |
| First main-library terminal failure | `_ctype_@LIBC` (OBJECT) in libyuanshen.so, hilog L3259 | addendum results.json |
| Earlier MHY `__assert2` | L3118/3119/3144/3145; execution continued; not proven terminal | addendum |
| `__register_atfork` | 0 messages; the error point moved; provider, semantics and winner not proven | addendum |
| maps | sample 22:02:06.658 precedes the failure; winner UNKNOWN | addendum |
| Restoration | 319 direct + 319 parent-view hashes, mounts, Boat3, control image, power SLEEP/30000/10000; closed at 978.404534 s | closed |
| Held check | later read-only recheck at 22:13:48 (rc1, empty); not the original unlock receipt | closed/postclose-held.json |
| Execution archive | 69,799,110 B, `8844053f…`, remote SHA-verified 22:22:56; snapshot predates the held recheck and final peer review | closed/remote-archive.json |
| Private addendum checks | 46 references passed in the original inner worktree; main lacks private dynsym inputs | closed/README.md |

The candidate is not the current deployment. Nothing is frozen. Only one app is involved, so the
two-app freeze condition is not met, and nothing is playable.

## Checks

`check_observation.py` reuses the G29 checker, which now requires the 61-row prefix and accepts later
rows. G29's offline-candidate guards are unchanged. A 62nd row is a positive check, and truncation below
61 or a later row with a missing reference is refused. On top of that, G31 requires:

- exactly 62 rows; row 62 equals [added-row.json](added-row.json);
- independent semantic guards (game failed, baseline restored, not deployed, not frozen, the atfork, maps,
  held-receipt and private-check boundaries, and the archive snapshot scope);
- every one of the 41 new references verified by SHA and bytes, limited to the five accepted G28/G26 directories;
- cross-checks of the closed, addendum, held and both archive receipts;
- byte equality of `index.html`, `observations.csv` and `results.json` with the original renderer's
  output for the checked JSON (through G25).

The G15, G17, G25 and G29 prefix checks run first. 18 negative cases are refused for the expected reason:

- history drift, a G26 row freeze claim, and false success;
- an HTML-only fake game frame and a CSV-only edit;
- truncation to 61 and a 63rd row;
- a row 62 edit and dropped evidence;
- playable, frozen and current-deployment claims;
- an atfork semantics claim and early maps read as final visibility;
- a fabricated unlock receipt and a claim that main reruns the private checks;
- a missing reference and SHA drift.

Status ordering: the first draft status began with row 60's full status text, so G25's HTML-forgery case
found that text twice in `index.html` and refused. G25 is outside this card's paths. Row 62 therefore
puts `candidate_currently_deployed=false` before `已恢复基线`; the meaning is unchanged. Each of rows 60–62
now renders its status text exactly once.

Actual run: [check.stdout.txt](check.stdout.txt), [check.stderr.txt](check.stderr.txt) (empty), [check.rc](check.rc) (0); Rust targets for G15/G17/G25/G29/G31 in [rust-tests.txt](rust-tests.txt) (5 passed).

## Rule set here

A deployment trial gets its own row next to the candidate row. The candidate row stays unchanged. The
trial row must state the real game outcome, the restored device state and each boundary on what the
evidence cannot show. Each boundary is enforced by a semantic guard, not just by equality with the
stored row.

No device, REA, runtime build, G14/T38 or push.
