# G33: append the G30 locale ABI candidate as API observation 63

## What was wrong before

Observation 62 recorded G28: the game failed, and the first main-library terminal failure was
`_ctype_@LIBC`. G30 then built an offline locale ABI candidate for that cluster and landed it on master
`8acf1ed61` (56 public paths). The API table did not yet point to its source, builds, tests or limits.

## What this adds

One row, `OBS-20261021-G30-LOCALE-ABI-CANDIDATE`, after the strict 62-row prefix of master `e4cd7d753`
(`observations.json` `69c19ae0…`). The 315 atlas, the renderer `render.py` (`0276c50e…`) and all prior README
lines are unchanged. The row references exactly the 56 paths in `locale-abi-candidate/final/landing-paths.txt`:
12 source, 14 build and 30 evidence. All 56 are byte-identical between `8acf1ed61` and the branch base
`5cf5a989b0` (see [input-pins.json](input-pins.json)).

| Fact | Value | Source |
|---|---|---|
| Baseline | `d2053066…` (39520 B) reproduced exactly | final/baseline-receipt.json, results.json |
| Candidate | `4296f805…` (41984 B), two identical full builds | final/results.json, candidate02-bookends.json |
| Added exports | `_ctype_` (8-byte OBJECT pointer to a 257-entry table), `strtoll_l`, `strtoull_l`, all under `LIBC`; no `__assert2` | evidence/elf-review.json |
| Preserved | 44 dynamic-symbol tuples; 26 prior defined exports, with exactly 3 added; old objects byte-identical; NEEDED `libc.so`; constructor/destructor sequences | elf-review.json, baseline/candidate-symbols.txt |
| Inputs | 55 hashed before and after candidate 02, all equal, with persistent copies | candidate02-bookends.json, input-closure.json |
| Host tests | 257 classifications + 90 integer cases (real locale code); native code with dependency stand-ins; 9 ABI guard cases | host-receipt.json, preservation-receipt.json |
| History kept | VM entry rc124 (environment, not compiler); host01 errno assumption failure, host02 passes | build-checkpoint-01, final/README.md |
| Archive | snapshot of the fixed G30 landing `8acf1ed61`: raw logs on local persistent storage, no remote receipt among its 56 public paths or its tree, so remote was not verified at that time | final/raw-index.json, landing-paths.txt, input-pins.json |

Limits stay explicit:

- no complete Linux OS or host library closure, and no OH semantic validation;
- the runtime namespace winner is UNKNOWN, and OH callbacks were not executed;
- the candidate is not deployed and not frozen;
- only one app is involved, and there is no game evidence.

## Checks

`check_observation.py` reuses the G31 checker, which now requires the 62-row prefix and accepts later
rows. G31's G28 failure semantics are unchanged. A 63rd row is a positive check, and truncation below 62 or
a later row with a missing reference is refused. On top of that, G33 requires:

- exactly 63 rows; row 63 equals [added-row.json](added-row.json);
- references equal to the 56 fixed public paths, each verified by SHA and bytes;
- semantic guards for each limit above;
- cross-checks of the G30 results, ELF, bookend, host, preservation and rc124 receipts;
- the archive snapshot, proven only from the SHA-pinned G30 landing list and `input-pins.json`
  (`archive_snapshot`: no remote receipt in the `8acf1ed61` tree or landing list), never from the current tree;
- a positive case: a temp source root that only adds a later genuine-shaped
  `final/remote-archive.json` still passes with the same reference count.

The G15, G17, G25, G29 and G31 prefix checks run first, including original-renderer byte equality of
`index.html`, `observations.csv` and `results.json`. 20 negative cases are refused for the expected
reason:

- history drift, a G28 row success claim, and false success;
- HTML-only false success and a CSV-only edit;
- truncation to 62 and a 64th row;
- a row 63 edit and dropped evidence;
- frozen, current-deployment and playable claims, and a remote-verified claim without evidence;
- a snapshot pin rewritten to list a receipt, and a landing list containing a receipt;
- full OS closure, rc124 as a compile failure, and `__assert2` inclusion;
- a missing reference and SHA drift.

Actual run:

- [check.stdout.txt](check.stdout.txt), [check.stderr.txt](check.stderr.txt) (empty), [check.rc](check.rc) (0);
- Rust targets for G15/G17/G25/G29/G31/G33 in [rust-tests.txt](rust-tests.txt) (6 passed, rerun for revision 2).

## Revision 2 (after outer review of 7e3c3e6cbc)

The first delivery, `7e3c3e6cbc`, required `final/remote-archive.json` to be **absent from the current
tree**. That made the historical row depend on a future file never existing, so a legitimate later
archive receipt would have shown up as a regression. Revision 2 states the archive status as a snapshot of
G30 at `8acf1ed61`, deletes the current-tree `exists()` check, and proves the snapshot from pinned sources
only. The 7e3 delivery is kept unchanged in history.

[discriminate_7e3.py](discriminate_7e3.py) runs both checkers against a temp root that only adds a later
receipt ([discriminate.stdout.txt](discriminate.stdout.txt), rc 0):

| Checker | Result on the later-receipt root |
|---|---|
| 7e3 checker | `REFUSED: a remote receipt now exists` |
| revised checker | passes with the same 1520 references |

## Rule set here

A source/build observation cites the candidate's own fixed public landing list as a whole, so a
reference set that drifts from that list is refused. An archive status in an observation is a dated snapshot of its fixed
source commit, proven from pinned inputs. A later genuine receipt does not make the old row false; it is
recorded as a new observation.

No device, REA, runtime build, G30 source change, G14/T38 or push.
