# T23 closed EGL-import candidate window

Candidate feed visibility, a human report of sound, and changes in UI/progress do not establish controlled video playback. T23 closed with runtime restored but UI not recovered: `CLOSED_RUNTIME_RESTORED_UI_NOT_RECOVERED`. No video PASS is claimed.

The 5cd window lasted 1422.324217 seconds under the original outer lock. Root actually applied six candidate states and rolled them back, both rc0. Shim production-02 was `a9abaf09ce020c45dea5a30d1030a8ae7f939a2f4434cd6ff3aec53cfc9726b6` (77,792 bytes), not the rejected/superseded production-01. Executor `693448c2…` and the other five candidate states were unchanged. This whole window was not read-only. This lane's brief delegated read-only HDC attempt timed out after 10 seconds (rc124, no completion marker); root resumed sole device execution. The earlier exact-MAIN lock check failed because kill-zero returned EPERM. Both raw lane failures remain unchanged.

## Actual evidence and limitations

- The candidate screenshot [feed](final/images/candidate-feed.jpeg) shows the news feed. Root's original first host-only image remains in the archive.
- Cycle 1 has four original screenshots at offsets 0/5/10/20 seconds, all SHA-identical. Cycle 2 shows a tutorial overlay followed by black content; UI/progress differences do not demonstrate video frames. The eight exact images and receipts are in [image review](final/image-review.json).
- [Human audio receipt](final/receipts/human-audio-receipt.json) records the user's report of audible sound during this window. Exact clip is unknown and the user may have touched the screen while adjusting volume. It proves neither two controlled cycles nor automatic continuous playback across different clips.
- The initial full-prefix stream hit a 60-second host timeout. Subsequent file-based copies returned complete selected prefixes: 33,156,759 bytes, SHA `73f7cd8497e5a9d85b8fc26cbbd2415985ed9e3c94db05580e560ec51d80fd14`; and 52,899,334 bytes, SHA `03f0adb2799f511d41d5178bbdb7ad83b2cf3cfd3e1c74c958361a6761d3fa56`. Both explicitly retain `immutability_not_proven=true`. Full raw logs/URLs remain private. This packet does not substitute a new technical root-cause interpretation for video_plan's analysis.

## Restoration

The actual six-state rollback, fresh boot `3b5f626e-e50a-416f-b7e5-29f754bc5945`, physical/private original five SHA values, absent compat, power10000/10000, ready and absent debug parameter106 are preserved. Independent [comparison](final/independent-restoration-comparison.json) finds all eight fields equal for the 518-target/812-label snapshots and all 26 supplemental targets equal excluding only the boot header. The initial before-snapshot 60-second timeout remains alongside the complete r2 acquisition.

The final [restored screenshot](final/images/restored-host.jpeg) was independently viewed and is Westlake IME host only. This is not feed restoration. Unlock rc0 and held-after rc1/empty are preserved; no lock remains claimed by this lane.

[run_facts](final/facts.txt) was run directly on the existing window, without synthesizing records:

```
TOTAL keys=2 screenshots_captured=2/2 alive_t5=0 alive_last=0 alive_unknown=2
```

Its denominator contains only candidate-icon and restored-icon with record.json. The eight cycle images have separate screenshot receipts and are not silently added to run_facts totals.

## Archive and reproducibility

The complete closed window, `t23-readonly-01` (including failed first snapshot and r2), candidate input binaries/manifest, and all ten existing root `t23_*.py` helpers are included. Lane handoff failures/preparation receipts and exact producer source/build files are included separately in the same private archive. All 12,140 members were read back and checked for SHA and size. No unrelated old windows were added.

Archive SHA `e5ef04efb0257b1d133856ab92883d1892a2bde741b778e8637f25939f247afb`, 22,373,188 bytes. [Pending receipt](archive/pending.json) remains pending until outer executes the three exact argv in `.private/archive-01/remote-commands.private.json` and verifies remote SHA/size. Outer subsequently executed all three original argv with rc0 and verified the remote SHA/size. The [success receipt](outer-success/receipt.json), [verification](outer-success/verification.json), and [raw argv/stdout/stderr/rc SHA index](outer-success/source-index.json) record that later success. Original pending/failure receipts remain unchanged; the tar was not repacked. Public argv use aliases; exact original argv remain in `.private/upload-01/`. This is archive persistence, not a Git push.

Source/build/producer references are indexed in `final/source-build-pins.json`; raw-to-public transformations in `final/source-index.json`. Public helper copies are historical execution sources with user-path aliases, not blind rerun entry points. The exact original helper bytes are retained privately. The API36 proposal is additive only: it does not modify prior 35 observations or signed 315 API rows/grades.
