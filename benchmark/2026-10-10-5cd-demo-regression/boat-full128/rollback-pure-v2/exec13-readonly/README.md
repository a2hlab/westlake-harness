# Read-only diagnosis of the post-rollback execv EACCES

The Boat source withdrawal and pure-U13 byte restoration succeeded, but the HW recovery gate failed. Identity is not execution readiness.

## Observations

1. `mount-delta.json` compares the saved working-boot snapshot with the current boot. The host bind gained `nosuid,nodev,noatime`; it has **no `noexec`**. `/data` changed in the same way. Before: boot `3c0a3eba`, parent4516 demonstrably launched Boat under Enforcing; after: boot `6898d2a5`, repeated init `execv 0 13`, no persistent parent.
2. `source-target.txt`: seq2 and target are root:root0755, `appspawn_exec`, 646760bytes, SHA `2a87118e…`. Parent directories have search bits. `init-view.txt` proves PID1 sees the same target SHA/label and the same `nosuid` bind, so shell-only identity is not the issue.
3. `boat-actual.txt`: the retained cfg starts the Boat worker after ready=true. Current log says `[20:30:05] FAIL MISSING_BOAT_SOURCES`; the script checks source-directory presence **before** its first bind. Its target set contains only three shared Android members and three app-private files, never appspawn-x. It does not remount, change enforcement, or launch apps. Removing the Boat job has no demonstrated causal path to this host exec error.
4. `dmesg.txt`: init repeatedly reaches `ServiceStart started`/`ServiceExec`, then `failed to execv 0 13 appspawn-x`, exit23. No `ServiceStart invalid:appspawn-x`/`pathArgs invalid` in this retained buffer. INVALID is not the observed active failure; the older start history before buffer rollover is unknown.
5. DIGEST806 describes INVALID before ServiceExec; current execution reaches ServiceExec. The earlier61b EACCES case in its restore evidence had a `system_file` host and was repaired to `appspawn_exec`; current labels already match that repair, so blindly repeating the label fix is unsupported. No relevant avc in the captured kernel buffer does not prove that no security check failed.

## Proposed minimal experiment, disabled pending outer approval

Leading **hypothesis**, not yet verified: the new host bind's `nosuid` prevents the service's requested execution-domain transition. Restore **only that bind's** flag to the already-observed working state, rather than changing `/data` globally, SELinux policy, cfg, bytes, or Boat members:

- Capture current host mountinfo/source/label/mode/SHA and current boot again.
- Remount the existing host bind with `remount,bind,suid` (preserve its other flags; no new bind).
- Read back PID1 mountinfo: the host mount alone has lost `nosuid`, `nodev/noatime` remain, SHA/label/mode unchanged. If command/readback refuses, stop.
- One ordinary `Deployment.start` attempt, then exact init parent/exe/socket checks and HWt20.
- If it fails: return the host bind to `remount,bind,nosuid`, read back, retain lock and evidence. If it succeeds:319/dual fingerprints + screenshot outer review, then unlock as authorized.

This is a proposal only. **No remount/start/reboot/config change was performed during this read-only diagnosis.** A bare reboot is not the preferred first experiment because it can reproduce the same flags and adds boot/USB risk. Further kernel-policy provenance is unresolved; a successful experiment would support this hypothesis, not prove every underlying policy detail.
