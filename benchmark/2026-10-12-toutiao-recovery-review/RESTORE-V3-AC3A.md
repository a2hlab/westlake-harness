# Actual disabled restore v3 review

**Offline independent pass, not deployment or seal admission.**
Frozen `ac3a78041ff0d36acb4d893b3602185aed1924a6285e6ce6d6dabe1de5f0a2f0`;
provider `cd2056ca74d9c608bfe87bf0a059b3fec6d75413e44224b1d7cc06ad59a8cd75`.

## Verified objects and tests

- All23 frozen objects and490 manifest members independently checked for SHA
  and size, then copied to a private immutable review snapshot.
- Manifest `de8a51c9…`, plan `8b82193e…`, executor `496fa979…`.
- Actual disabled binding:486 members (23 controls,460 runtime,3 stage),22 new
  directories,6 existing-directory guards; execution remains false.
- Independently ran the7 actual-binding recording-transport scenarios:7/7,
  exit0,15.941 seconds. Author14/14 includes7 other base checks; this review
  does not claim those14 were all independently rerun.
- Actual standard CLI preview: exit0, `PREVIEW_NOT_RESTORED`, no output directory
  created. One changed exact-seal member SHA: exit2 before transport.
  These CLI documents are explicitly synthetic test inputs, not actual seals.

## Previously blocked rollback shapes

The actual absent CFG now has a dedicated branch: compare the observed candidate
SHA, use guarded remount/ro reseal, remove the newly added CFG and read back
absence. It does not read nonexistent before metadata or reactivate an unsafe
donor. The full apply/rollback scenario verifies the real absent shape.

Directory creation records intent first and ownership only after complete
metadata plus dev:inode readback. Cleanup checks plan/target/metadata/identity,
uses only `rmdir`, and refuses unknown, nonempty or replaced directories. A
failed metadata/readback cannot be upgraded to owned merely by matching mode.
Failures retain bytes and produce an immutable unsuccessful partial receipt;
success is published only after cleanup. Same-transaction retry is covered.

Fresh cases include first-mkdir failure, metadata/readback failure, retained
nonempty data, partial send with exact observed bytes, same-metadata inode
replacement and unknown directory. No app/parent signal or recursive user-data
removal occurs in these scenarios. The execution transport is a recording
model, not HDC or a real board.

## Binding boundaries still pending

The three archived/current/generated script digests are explicitly listed in
the frozen derivation audit. Current221 has218 unchanged and3 known UID/WID
derivations; the extra239 sources have their actual closure evidence. This is
not a claim all460 currently deployed bytes equal the archive.

The exact-seal checks remain unchanged. Same-board startup may rewrite run.sh
WID, and cross-board UID/serial/attempt derivation changes scripts and manifests.
No canonical/dynamic-field exception was added. The separate origin-seal/spare
realization decision and authorization remain with the user/outer owner.

This package derives the accepted alias baseline, not the new t9 guardian by
implication. Integrating t9 requires a new composition and fresh complete pins.
No new authority, signature, UI acceptance or reboot persistence is inferred.

## Evidence location

`restore-v3-review-results.json` records the exact object hashes and fresh
receipts. The23-source/490-member snapshot persists under
`.artifacts/restore-v3-ac3a/`; small raw test/CLI records accompany this report.
The earlier81af rejection remains historical and was not overwritten.
Zero board, VM, remote, candidate, gate or frozen-file modifications.
