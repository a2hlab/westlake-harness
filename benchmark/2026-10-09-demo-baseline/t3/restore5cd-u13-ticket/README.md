# 5cd signed U13 recovery

The new boot exposed the underlying system, not signed U13. The old recovery journal was refused before locking because its native policy ticket had drifted. Outer ACK(91) at 00:50 authorized a fresh ticket limited to the already-signed U13 baseline. The original journal stays unchanged; only `plan.native_tickets[1]` changes in its clone. All 319 baseline hashes equal the independently recorded U13 recovery inventory.

The existing executor replayed 56 baseline layers without reboot, startup configuration or candidate artifacts. Original runtime/boot fingerprints are 821de739cf81 / ee927db88a67. Final identity has 319 paths, empty diff/absence; parent/child byte views and one ART/JVM pass. Original restored smoke PASS, both controls alive at t20, images retained for outer signoff. Lock was released and rc1/empty holder confirmed.

Three smoke attempts before r4 failed before any app record: the first lacked VM `hdc`, the second resolved the default lock script below the VM HOME, the third queried VM-local instead of Mac-held locks. This was recovery wrapper configuration error. r4 uses the existing `hdc_mac.sh` and the exact `mac board_note.sh` prefix from production DeviceIO. No acceptance rule changed. Those logs remain in the raw directory and are not UI evidence.

Raw journals, command logs and ticket reports remain under this directory; `ticket-audit.json` binds original and cloned journal hashes and all baseline bytes. No binary runtime input is included in this evidence landing.
