# Fixed5cd low-fork metadata: actual A/B and independent raw review

The earlier candidate was locally equivalent but had no OH timing or complete currentboot512 observation. This fixed5cd run now establishes both original/candidate metadata output equivalence and the timing below, for one ordered A/B only.

| Metadata phase | Objects / batches | Elapsed |
|---|---|---:|
| Original external dirname |512 /23|135.004937s|
| Candidate shell parent calculation |512 /23|15.949347s|

Observed metadata time fell by119.055589s (88.1861%), an8.4646x ratio. Each phase additionally made four boot/18SHA bookend reads; those and holder checks are excluded from metadata timing. Per-call metadata sums differ from enclosing phase timers by only0.0252s/0.0233s. This is a single old-then-new run: cache/order/load effects remain, and it is not a measured full954/128 speedup.

Independent review read all23 original and23 candidate raw batch outputs, verified all512 rows against the exact same expected metadata, and compared ordered bodies byte-for-byte after stripping their unique success marker. All108 stdout/stderr files were hashed, stderr was empty, and every success marker was0. Both before/after bookends matched boot `c9436daa-b3ca-44dc-985f-9ee03445567a`,18 candidate SHAs, and all four exact canonical holder receipts on serial `5cd1e3dd00000000000000000923012c`. No result is borrowed from61b. Raw pins are in `raw-receipt-pins.json`.

Evidence chain:

- [Measured original bottleneck](../2026-10-14-identity-performance/README.md):4,993 external dirname calls; unequal native954 comparison explicitly rejected.
- [Independent candidate and original offline matrix](../2026-10-14-identity-lowfork-candidate/README.md):12 scenarios,566 parent cases, original helper7059cc45 and candidate9ab15ecd; same per-object guards, parser and transport.
- [Independent disabled5cd package review](../2026-10-14-lowfork-5cd-independent-review/README.md):507files+5dirs regenerated from actual5cd provenance, three tests and preview passed.
- [Durable original raw archive](../2026-10-14-lowfork-5cd-archive/README.md): `hw248:/home/alvin/westlake-metadata-lowfork-5cd-20261014T012214-016918ca/metadata-lowfork-5cd.tar.gz`, SHA256 `4da142c3aa10d3ad4b09c86e8ddcc82a5656298276cb3294e1bb087630091770`, 40,124 bytes.

Root reported session75745 exit_code0 and empty canonical held output after its trap released5cd. The source stayed frozen throughout archive verification; no closeout marker was injected. Raw logs stay in the archive, while the small reports and source candidates can be reviewed/submitted separately.

**METADATA_AB_PASS_ONLY.** Current61b full128 continues with its original pin. This result does not replace full954 identity, remove an epoch/guard, demonstrate full128 equivalence or grant deployment authority. Reviewer performed zero HDC calls, source writes, commits or pushes.
