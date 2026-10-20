# T29 shim peer review: passing tests did not validate failure records

Checkpoint 01 passed an independent rebuild and all **12 logger + 27 real routing cases**, yet request, map and allocation failures still logged the successful cache stage/raw return. A conversion failure logged an uncalled flush's default zero. Those results could misidentify the first failed operation. The original findings and before/after raw fixture stderr are preserved here; the earlier green result is not rewritten as source admission.

The revised code separates operation stage, raw-result validity, normalized return and cleanup results. Independent recompilation then passed **14 negative cases with parsed actual-log assertions**, plus `valid` and `errno_route`. Final checkpoint 02 changed only the fixture/checker relative to that peer-tested runtime source; four additional negative cases (layout, handle, native conversion, positive provider error) were independently rebuilt and passed their field assertions. Thus the final delta independently covers **18 negative cases plus two positive cases**. Unchanged inherited core tests were not rerun.

| Injected failure | Before | Accepted record |
|---|---|---|
| request -19 | cache stage32/raw0, public -19 | stage37, called/raw_valid1, raw -19, public -19 |
| map -5 | cache stage32/raw0, public -5 | stage46, raw -5; cleanup separate |
| allocation/prepare | cache stage32/raw0 | stage48 with actual prepare result |
| before-Unmap conversion | stage42/raw0 from uncalled Flush | stage49, conversion -22; Unmap/Abort recorded independently |
| positive request result7 | not part of first independent delta | raw7 preserved, public -5; no fabricated raw/public equality |

All **47** files in the final author manifest were independently size/SHA verified (`1300943a40ffc1fa7b047b42adbdbd733e9c9b88caf160e85049a83fc093dc98`). Source differences were reviewed against the previous pinned copy. Return, pixel/format/ref/cleanup assertions remained passing in the executed real exported-shim → pair → typed adapter → R14 paths. The logger's sink, quota and pthread tests are host evidence; no claim about a runtime provider winner or playback is made.

Status: **shim checkpoint02 source review accepted, host only**. Consumer method review, new bridge owner/GOT offsets, final production and any device admission remain separate. No HDC or new REA calls occurred. `private-index.json` locates original snapshots, argv/stdout/stderr/rc and reviews; every prior failure remains preserved. Public selected stderr is synthetic fixture output with no media/user data. `landing-paths.txt` lists only this package, so the outer coordinator can add repository navigation separately.
