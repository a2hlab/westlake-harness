# T70 — current deployed launch inputs and ordinary startup errors (61b, boot 33f35797)

Read-only, no lock needed (board free, `held` rc=1), zero device writes, no reboot/reopen, no REA/debugger/tombstone/FD2.

## What was missing before
T69 could only compare HAP/cfg hashes read on the *pre-reboot* boots; the post-boot deployed launcher/guardian and any ordinary startup error output were unknown.

## Evidence
- 13 exact regular files hashed on the current boot (same boot as the T68 failure), paths taken only from our own source (`real-start-parent.sh:13`, `config-common.sh:21`, `members.tsv`) or from our own log line. See `evidence/file-sha-stat.txt` and `results.json.files`.
- All 10 checked launcher/config members match source bytes or recorded expected hashes: HAP b18978b8, toutiao cfg 7b9f2c0e, recover-v3 cfg 897f9ca0, root and per-boot `watchdog.sh` 8bf74a08, `boot-entry.sh` 7fbfdf05, `entry.sh` ad76c656, `real-start-parent.sh` 8e1d214e, `launch-common.sh` d065f354, `screen-gate` 0bf966d7.
- `/data/local/tmp/asx/run.sh` is not visible in the hdc shell (No such file); it is only referenced inside `source_app_namespace` (unverified, no context change). The app `run.sh` under `/data/app/el2/.../files` was not read (app data tree).
- `parent.log` (our redirect): ART start and framework preload OK, child pid 8088 spawned, child stderr redirect opened, last line `[WESTLAKE-REAP] child 8088 killed by signal 11`.
- Child stderr `adapter_child_8088.stderr` (path bound by the parent.log line; mtime 12:14:57.76, inside the guardian exit window): no class/library/permission/entry error or exception/signal text in the captured last 200 lines; last lines are window/surface session setup.

## Result
The checked launch inputs match recorded expectations. Outer review directly hashes six local source entries; three HAP/config values match prior receipts, and the screen-gate executable matches the committed package manifest (its binary is absent in the outer mainline checkout). This is not an audit of all native/runtime artifacts. Ordinary output shows **exit only** (signal 11 reported by our reaper) with no explicit controlled error. The cause is not attributable from ordinary output; the last stderr line is not evidence of the fault site. No fix or retry is proposed.

## Rule
A child exit by signal with clean ordinary output is a gap, not a configuration finding; do not retry the device trial to "find" it.

Independent review: [outer-review.json](outer-review.json); 57 private manifest entries and nine cited raw receipts verified. Original author results remain unmodified.

Private original command receipts remain at `$HOME/.local/share/westlake/current-launch-readonly-20261023/`; manifest SHA256 `595a75bbc3d533f3a2d310e13bfa993ee63728adc42c82d70eab6d892b5e7758`. Public excerpts contain no credentials or full MAC addresses.
