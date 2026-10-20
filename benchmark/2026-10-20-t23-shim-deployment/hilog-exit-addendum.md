# Preserve logs after child exit

This addendum clarifies the accepted seven-file observation card without changing its frozen bytes. PID-filtered hilog remains useful after the sampled child exits. Preserve the full `hilog -x -P PID -z 2000 -L D,I,W,E,F -v epoch` stdout/stderr/rc even when the postguard fails or /proc/PID disappears. Mark postguard UNKNOWN/EXITED and record the last proven boot/PID/birth plus the current boot observation. Absence of /proc does not establish that every returned line belongs to that birth. PID reuse and buffer history require time/provenance qualification; do not rebind lines to a new child or discard old lines. No time-range CLI is inferred from epoch output.

If the child is already gone before collection, perform only the authorized boot/holder-bounded historical PID-log read, not memory/maps reads through that dead identity. Keep it separate from live-identity-complete evidence. No repeated icon or restart is authorized by collection failure.
