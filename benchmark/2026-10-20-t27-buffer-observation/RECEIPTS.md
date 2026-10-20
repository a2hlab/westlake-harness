# T27 observer — frozen receipts (host, offline; no device)

Raw build/run receipts (argv + stdout + stderr + rc) and artifacts persist under
`$HOME/.local/share/westlake/t27-observer-cc/` (gitignored binaries/logs kept out of the public repo):
- `build.argv`/`build.std*`/`build.rc` — `cc -c observer.c` → **rc 0**
- `test-build.argv`/`test-build.std*`/`test-build.rc` — `cc -I. test_observer.c -o test_observer -lpthread` → **rc 0**
- `test-run.argv`/`test-run.std*`/`test-run.rc` — `./test_observer` → **rc 0**, stdout `T27 OBSERVER TESTS: PASS`
- artifacts: `observer.o`, `test_observer`, `emit_smoke`/`emit_smoke.c`

Frozen source SHA-256:
- observer.c  `0a31347c0c8499d5109b9ef73c84b1dab42ea78fac58c7ece08a884dc0814521`
- observer.h  `d60cf01a30a600348451de6b9b25a86ab5a1a2ff651fa1bddfe04ef6d1cf516b`
- test_observer.c  `418da084c4833541ac89d003ab460e4d6e1ddc07c993df39c7011b17dcda207a`

Covered by the host test (real C, typed fake provider/owner + canaries + fd-2 capture):
ABI SDK field order (usage@12/stride@16, sizeof 20, compile asserts) · pure-observer entry-errno preserved ·
create provider-errno preserved + single invocation + return propagated · admitted getter calls counted ·
NULL/foreign getter → zero calls + UNKNOWN · full line + newline (no 256 truncation, create_base/rel/ret present) ·
long file → explicit `<TRUNC>` + guaranteed newline with base/rel surviving · print-cap 256 + single drop marker +
ring drop counting. cx owns all integration glue; observer is frozen.

## Production receipt boundary
Function host test = VERIFIED. **Production receipt = NOT_YET_VERIFIED** (see `receipt.json`): the spec receipt
scenario (missing source/tool/raw-log rejection, check_frozen, byte-identical T25 baseline relink,
OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED) is verified ONLY by the final T26 joint-production package (cx), not
by the 6 green functional selectors. `ttvideo_t27_receipt` is IGNORED until that joint receipt checker exists.
root may admit the observer implementation + function host now; the production receipt is admitted by the joint package.
