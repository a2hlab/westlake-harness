# T6 r2 transport-only review

## Verdict and exact objects

**ACCEPT for the transport-only revision.** New freeze:
`842c4a0235c9ed1d0b4fe1b965cc6aa9a68c2d14d04f6498c96b70630d772e7e`.
All **16** SHA/size rows and **17** normalized landing paths match. The earlier
583230fa metadata checkpoint was superseded while ACK/README were being finalized;
its premature 11/11 board claim was explicitly withdrawn, not silently retained.

Restore adapter:
`af1ce6fc2f6b43568e8acec9f06cd63c92f48aa10c49c6b3a16c7c39258b2f05`.
Entrypoint:
`6a5b6bf5a1284304e14fa23def844db36b59c47b014faee1b981fe8bda3bd759`.

Only the adapter execute function changes: timeout **900→2700 seconds**, plus
explicit timeout UNKNOWN/124 receipt. Guard/prepare/checked_package ASTs are
unchanged. Lock lookup remains 15 seconds. Executor `496fa979…`, original
transaction, plan and 487 targets remain unchanged. CLI import selects this
adapter and frozen parent compiler; wrapper delta is only its explicit
realization dispatch path. Legacy fallback is byte-identical.

## Independent narrow checks

`check_t6_timeout_r2.py` exited **0**, **7/7** synthetic transport cases: success,
executor rejection, interrupted exit, rollback budget, timeout UNKNOWN, admission
failure with zero runner calls, wrong holder without executor call. Timeout
retains partial output and asserts neither process nor rollback state. Real CLI
`--help` and shell syntax also exited 0. No real child executor, lock or device
was invoked by these fixtures. Raw results and final freeze verification are in
`evidence/base-placement/t6-timeout-r2-{review,freeze}.json`.

The actual old attempt's 332 completed raw command JSON mtimes span 110.677s:
mean **0.33437s**, median **0.32188s**. Exact successful control flow requires
**3539 calls**: 2×518 fresh + 22×3 directory + 486×5 ordinary placement + 1×6 CFG
+ 1 preserved readback. Mean-rate projection is **1183.34s**, or **1415.6s** at
0.4s/call, before additional large-file transfer costs. This is a measured-risk
projection, not a guaranteed duration. The old 900s cap was unsafe. Outer stopped
that host process before any transaction/member/directory intent; original raw
evidence is retained. New execution must use a fresh transaction and a newly
pinned admission generator SHA, expiry and authorized lock window.

## Concurrent selfcheck gap

The disabled proof and activated preview differ at exactly **two** full-file
hashes: startup.env and startup.expected.sha256. Current running_files only
derives WID, so the original selfcheck will reject those activation differences.
Evidence is `t6-activation-selfcheck-gap.json`. This does not invalidate r2
placement. R3 must explicitly bind prepared/admission/actual apply receipt,
reproduce the original prepare output exactly, verify real executor rc0 plus
487 exact placed tickets/transaction, replace only those two expected SHAs, then
derive the single independently observed WID. No exclusions, no timeout receipt
as success, no fake seal. The r3 implementation remains a separate review.
