# T14 existing-child normal-play observation — review candidate

The T12 bottom-tab click did not establish player creation. This task observes
one visible play action, with a same-process bounded stderr delta. It does not
repair optional libraries, launch a guardian/app, or broaden T13. Device
execution and visual acceptance are pending outer review.

## Inputs and reuse

Fill profile.template.json from a new outer read-only receipt. It deliberately
has no T13/T12 child, parent, boot, or executable defaults. Bind parent, child
and host PID/PPID/birth/UID/exe/mount namespace, fresh run SHA and private-mount
relationship. Supply that raw receipt via --receipt; its SHA must match the
profile. `observed_at` must be within 120 seconds at begin. A changed child
requires another reviewed window; no discovery/reselection occurs.

The implementation imports the existing bms_batch.Board (lock, boot, remote
return marker and screenshots), and the existing log-delta Snapshot/range
checks. source-pins.json fixes both imported files. It does not edit them.
The subclass adds exact holder, retained monotonic deadline, identity guards
and preservation of TimeoutExpired stdout/stderr. Power restoration uses only
same-boot/holder guards, so a child exit does not prevent restoring the saved
override. A boot/holder loss blocks restoration and requires outer recovery.

## CLI sequence (outer only, fresh persistent window root)

Common arguments: `--repo REPO --profile PROFILE --receipt RAW_RECEIPT
--root NEW_WINDOW --hdc HDC --holder EXACT_HOLDER --start HOLDER_EPOCH`.
Every invocation is preview unless `--execute` is present. The outer holds the
5cd lock before execution and does not release it until power readback succeeds.

1. `begin`: fresh identity guards, persist original Timeout/Override, temporary
   awake, create only a unique t14 scratch directory, capture the current screen.
2. If necessary, `ui --kind unlock --coords X1 Y1 X2 Y2 --reviewed-sha SHA`
   and/or `ui --kind front --coords X Y --reviewed-sha SHA`: coordinates must be
   selected by the outer from that action's latest screenshot. Front means a
   normal UI choice for the existing app, never a shell launch. If no such
   visible path exists, stop and restore. Each kind is allowed once.
3. `capture`: identity-bound screenshot, maps and WMS. The outer confirms real
   feed/current video UI. Optional `ui --kind tab ...` runs at most once.
4. `log-start` immediately before play: pin regular fd2 target/device/inode/size.
   Then `ui --kind play ...` once, selected from the current screenshot. The
   intent is persisted before touch; timeout/unknown is never retried.
5. `log-read`: one same-child, same-inode read, up to 65,536 bytes starting at
   the pre-play offset. `capture` can obtain a later screenshot and maps. If a
   delta is capped, no assertion about unobserved later bytes is permitted.
6. `restore`: restore original Override with `-o`, verify both original fields,
   mark stopped. UI/read work stops at 540 seconds; only restoration may use
   the remaining 60 seconds. Failure triggers immediate restoration attempt.
   After 600 seconds, this tool refuses further commands; outer recovery is
   required if restoration has not completed. No lock release is automated.

Each successful uitest is followed by reapplying the temporary awake value,
because uitest has previously reset the short timeout. Actual UI results and
playback remain human review. Missing feed, no visible play target, identity
drift or missing actual player load evidence means unknown, not a guessed fix.

## Merged HDC framing

The outer's read-only printf probe proved remote stdout/stderr are merged into
host stdout. The former separate-stderr delta recipe is retained unchanged and
is not used for T14 transport. framing.py emits a unique header with the exact
requested byte count, `dd bs=1 skip=OFFSET count=N`, an exact-position end marker
including dd rc, preserved dd diagnostics outside the data frame, then the
same identity/file guards and a final marker. Only the declared bytes are
selected. dd diagnostics use a file in this window's unique scratch directory;
they are preserved in the raw combined output rather than discarded.

A short read, dd failure, missing marker, timeout, malformed frame or identity
failure is PARTIAL_UNVERIFIED and stops observation. Every raw command output
remains saved. The scratch file is an explicit temporary-evidence exception;
there is no production or application-data write. In-place log overwrite or
truncate-and-regrow cannot be excluded by inode/size alone. No incomplete log
can prove an exhaustive first fatal or that a config-string match executed.

## Validation limits

Six Python tests and the real Rust wrapper cover actual local shell/dd merged
framing, binary payload, short/error reads, missing marker, timeout bytes,
coordinate/repetition refusal, strict power parsing and preview zero-device
behavior. These are host tests, not board acceptance or full lifecycle proofs.
The two visual/recovery contract scenarios remain human pending_review. The
outer must independently review the fresh profile and this candidate before
execution; no board call was made while authoring it.
