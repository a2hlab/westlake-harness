# Final 61b dynamic evidence cross-check

ACCEPT: 15 local mechanical checks and 252 explicit local reference pins match. No dynamic-chain blocker was found in the filled, unsigned signoff snapshot `520a5b2d7556150845f09daa074d2a9cb0526c923822c21a9465fb9168838480`. The reviewer did not sign the seal, contact a device or remote host, modify archived sources, or rerun historical tests.

Evidence is recorded in `results.json`; reproduce with `python3 benchmark/2026-10-14-final61b-final-dynamic-review/check.py` from the repository root. This reads current evidence and rewrites only this review's result. A subsequent root signature changes the reviewed signoff snapshot and is outside this unsigned review.

- New realization points to unsigned seal `b319c9a3d77cb05713c7e677109b7c1654ae31a709a88651801f8de52a04f426`. The live result points to this realization, retains boot `086db6c7-a7e7-40ce-a336-9608adc05afc`, and contains 954 unique equal expected/actual checks.
- Capture has 824 distinct file paths and 130 APK paths. Its four file groups contain 829 entries with five consistent overlaps. All 48 original hash receipts match their pins; their 954 path/hash pairs equal the seal/package inventory and live check. Package ordering differs between the collector and sorted seal, but all package records match when keyed by package name.
- Both actual overlay admissions bind the current capture, root128 review, and UI review pins. Their exact member counts remain 487 and 18. Root128 authority remains `9c19f40f635125e725a82bf32a5485eab8fe1ae4318dc506fef0ec4908189ded`.
- All 24 original identity receipts pass with empty diffs and the same boot. All eight original smoke/after-lock/before-unlock tuples are zero. The original round records 128 keys. Exit observation explicitly retains a null global OS exit code; individual shard return codes are preserved.
- Second archive receipt matches `374b57b0d4fffaf504ad6608a9d37decd957fe49d9d7d8d89e4fd4fc03f3df43`; local archive bytes and its 2,320-entry source manifest match the recorded hashes. The three operations documents match across signoff pins, current files, source manifest, and extracted archive bytes. The signoff itself is absent from the archive.

Existing scoped startup-only, partial, excluded, content-state and functional limitations remain unchanged. The root's 115-item composition (109 core plus six existing partial entries) is not a new functionality grade. This review does not independently renew the remote archive receipt or adjudicate restore semantics; T4 owns the parallel semantic review.
