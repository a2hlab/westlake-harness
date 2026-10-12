# T10 capture-path adversarial design review

## Evidence first

The actual new boot `52533d3f-e49c-451e-a632-4902d77ffcb0` reached BOOTSTRAP for child 6590/birth8495 and 8883/birth10884, retaining parent4625/birth7158. The parent log explicitly reaps both children with signal11. This is separate from capture rejection: `r3-posttap/failure/summary.txt` records snapshot_display refusing the real parent directory of `F/current.jpeg`, requiring `/data/local/tmp`. Neither the failed captures nor surviving parent proves an app UI.

The historical working path shape is `snapshot_display -f /data/local/tmp/<name>.jpeg`, e.g. `scripts/lab/baseline_run.sh` and `scripts/lab/ttdrive.sh`. Reuse only that capture invocation shape, not their app-launch actions or fixed global filenames. Existing recovery.cfg already lists CAPTURE_SCREEN in both permission and permission_acls; this is not a proposal to modify permissions.

## Minimal implementation boundary

1. Use a new exclusively-created capture scratch location beneath the literal `/data/local/tmp`, bound to current boot and guardian PID/birth plus this capture's monotonically changing poll identifier. Reject symlink/non-directory parents, `..`, unexpected paths, and an existing scratch location. Do not adopt, chmod, clear, or recursively remove an unknown location. Atomic mkdir plus a recorded root-owned restrictive mode/dev:inode is sufficient for an exclusive directory; no new supervisor/lease subsystem is needed.
2. **Nested directory support is now established by new real-board evidence**, superseding the initial historical-only uncertainty: `r3-current-screen/001-capture.stdout` records successful JPEG capture to `/data/local/tmp/wl-r3-observe-d8ae2a5f09ce4d1ab4bfbb6844b31d37/current.jpeg`, 1200x1920, remote exit 0, boot52533, child11056/birth14027 with parent4625. Outer visually signed its normal image-containing Toutiao feed. Use the simple exclusive 0700 private-directory form mandated by t10, not a second direct-file fallback or a new native change. This observer capture proves permitted path shape and current visible content; it does not retroactively prove the old watchdog classified feed or published READY.
3. Start from a newly allocated empty output, never an existing photo. Reset label/feed evidence for this poll. Capture nonzero, timeout, absent/empty output, symlink, non-regular file, unexpected ownership/inode, failed copy/readback, or classifier failure must prevent classification as feed. A nonzero capture with a leftover valid JPEG is still a failure. Logs must identify the actual attempted pathname and exit.
4. Before publishing, retain current boot/guardian owner and current child PID/birth checks. Copy only that successful capture to the guarded F destination; verify regular/no-symlink source and destination, nonempty data, and byte-identical readback (existing cmp pattern suffices). The next poll must not consume the old current.jpeg if capture/copy failed. Either remove the guarded old current file first as r3 does, or gate all use on a per-call success flag; do not use existence alone.
5. Two feed observations must come from two successful capture invocations for the same child/sequence, not rereading one copied frame. Do not require different SHA values: a stable screen legitimately produces identical frames. A crash/replacement between capture and acceptance must not let the previous child's image mark a new child READY.
6. Cleanup only this transaction's exact file(s) after ownership/inode checks, then rmdir the owned empty directory. Preserve unknown entries or ownership drift; no rm-rf fallback, no broad glob, no recursive data cleanup. A failed cleanup cannot be reported as completed cleanup or trigger an app/parent kill.
7. Capture/copy/classifier failure stays UI_UNVERIFIED with feed_count reset. It cannot send signals, clear stop, rotate user data, recreate a parent, or turn a live child into an automatic crash-recovery attempt. Genuine process exit remains handled by the existing separate branch.

## Minimal frozen-candidate negative cases

- Existing unknown directory and existing/symlink output: refuse, preserve sentinel and symlink target bytes.
- Parent symlink/path escape, destination symlink, or inode replacement: no external write/delete and no classification.
- Capture rc255 or124 with a valid pre-existing/partial JPEG: no screen-gate invocation and no feed count.
- Capture rc0 with empty/missing output; copy/cmp failure: UI_UNVERIFIED, not READY.
- Successful capture/copy/classifier and then second independent capture: normal feed progression preserved; child/birth change cannot reuse evidence.
- Unknown scratch contents on cleanup: retained, no recursive removal; failed capture never kills the still-live app/parent.

This is a pre-freeze design review only. Review the new exact watchdog/helper and refreshed entry/member/startup pins after freeze; never modify or silently approve the historical r3 freeze. No board, VM, remote, app, permission, or candidate mutation was performed.
