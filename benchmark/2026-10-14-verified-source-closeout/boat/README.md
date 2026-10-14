# SOURCE-CLOSEOUT — Boat private production components

Previously the delivered historical overlay scripts pointed at three binary inputs, while the real
signal source and fixed-input transform recipe were external. This closeout adds executable offline
production recipes and preserves actual new executions. It does not alter a signed board, an API grade,
or any frozen output expectation.

* C7 and C4: 6 patchelf processes rc0; final two hashes equal the signed `1bea0fae` and `f6b806b5`.
* Signal: original two C units compile, link and strip successfully. New output `0987e589` differs from
  signed `7a931c79`; strict comparison returns rc2. Only `.note.gnu.build-id` differs (19 bytes).
* The existing MAIN `ddae7366` signal-source snapshots differ from the actual recipe-local `bb7732fa`
  source. This package delivers `bb7732fa` and its original musl backend/header/maps.
* New raw logs are preserved with actual command return codes. Original exact producer logs remain
  unknown. No old failure is discarded and no new execution is presented as an original one.
* The game source recipe preserves dfaa9ef / Unity2020.3.23f1 / camera patch / package locks and original
  Editor method. The large project build was not executed.

Implementation: [boat-v2-production](../../../sources/api-implementations/boat-v2-production/README.md).
Machine evidence: [results.json](results.json), [section comparison](signal-section-comparison.json),
`evidence/` receipts. `.artifacts/` contains raw streams and binary outputs, excluded from landing.
`persistence.json` states the actual local archive and remote persistence status, without inventing a remote PASS.
The 2 human scenarios remain subject to outer contract acceptance.
