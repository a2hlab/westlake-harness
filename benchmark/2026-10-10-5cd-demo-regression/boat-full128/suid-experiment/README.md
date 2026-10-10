# Single-host-bind nosuid experiment and recovery provenance

**Final board disposition:** after the separately approved one clean reboot, boot a565a760 has no nosuid on /data or host bind; Enforcing, current READY/56, strict319/diff{} and both fingerprints pass. HelloWorld own screen is visible at t20. Lock released; screenshot submitted for outer review. No Boat bindings remain. The earlier partial-recovery failure is preserved below, not rewritten into PASS.

Evidence precedes causal attribution. The current vendor fstab declares `/data` with `nosuid,nodev,noatime`; normal bind inherits its source mount flags. Saved boot 567ee543 mountinfo has `/data` and the host bind with `rw,relatime`, without nosuid/nodev. Current boot 6898d2a5 has the fstab flags. Both recover journals report 56/56, labels and READY, and neither records mount flags. The actor that changed the earlier `/data` flags is **unknown**; no audit trail demonstrates a late remount in the failed boot.

The exact on-board v2 script SHA matches master 95eb4f6e. Its bind loop line134 and master v3 line137 perform only `mount -o bind`; neither contains a host suid remount or a nosuid guard. Root rw/ro remounts in finalize_runtime target `/`, not `/data` or the host bind. Boat's missing-source check exits before the first bind; no host or remount action exists in that worker. Thus the shared recover omission is dependence on whatever source mount flags exist, not a skipped pre-existing suid step.

Master v3 SHA6b2a7cbb has the same omission. Its explicitly requested permissive mode may mask execution-domain checks, but it is not a fix to the bind flag. No 61b command or installer change was made. This risk note was posted before the 5cd experiment.

Outer authorized a single existing-host-bind remount with suid, readback of all mount rows and unchanged SHA/label/mode, then one normal start and HW t20 plus strict319. Failure restores nosuid and retains the lock. No global `/data` remount, new bind, enforcement change, cfg edit or reboot is permitted by this experiment.

## Approved experiment result

`host-suid-r1/mount-delta.json`: the full PID1 mountinfo changed only mount134, and only `nosuid` was removed. SHA/mode/label unchanged. Init parent28686 then execed the exact U13 host, PPID1, domain `u:r:appspawn:s0`. Strict319/diff{} and both fingerprints passed. This single-variable result verifies that removing the host bind nosuid clears the observed host exec EACCES barrier. It does **not** identify who altered the earlier /data mount, or certify child/UI recovery.

HW t20 is white, child absent. Captured raw hilog progresses to INSTALL_RESULT:0, ENTRY_RESULT:4294965293 (signed -2003), FAIL_PROVIDER and exit123. This is the observed next failure; no unsupported seccomp root-cause claim is made. Per the failed-recovery rule, the host's original `rw,nosuid,nodev,noatime` line was restored byte-for-field against pre-experiment mountinfo. The already-running parent was not stopped; the lock remains held. A final read-only319 after flag restoration still passes bytes/fingerprints and existing parent identity. No second HW run occurred.

The helper now treats a missing observed child as a hard recovery failure after preserving the parent/identity evidence. Screenshots remain a separate human review gate; script/parent PASS never establishes UI. All raw files have durable paths and SHA in evidence-index.json; full hilog is gzip-compressed losslessly.

## Clean reboot readout

`clean-reboot-r1/result.json` records one target-boot invocation and **zero manual bind/cfg changes**. Before the first app, PID1 mountinfo has `/data` and host mount135 `rw,relatime` (no nosuid/nodev), while fstab still declares nosuid/nodev/noatime. Receipt is READY/56 for boot a565a760; Enforcing. HW t20 has the actual HelloWorld interface and the recorded child is alive; strict319 and fingerprints452447a4a0ba/ee927db88a67 pass with parent4431. It was not retested. The lock was released per outer instruction.

Mount flags differ across boots despite the same v2 recover SHA95eb4f6e and unchanged fstab. This repeat rules out a permanently reproducible nosuid state under the current one-boot protocol; it does **not** resolve the actor/boot condition that selected different `/data` flags. Boot journal captures step timing/dmesg, not per-step mount flags, and the archived prior commands search found no matching data-remount command. Do not invent that missing provenance.

A repair candidate should make the exec bind invariant explicit and read it back before READY; this report does not implement a recover patch or broad source-mount changes. The new readout does not prove that removing nosuid from every child bind would repair the -2003 failure; that was explicitly not tried.
