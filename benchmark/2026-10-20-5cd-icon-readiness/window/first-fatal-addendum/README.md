# First fatal narrowed: foreground rejection before child spawn

The preserved `spawn.txt` explicitly reports `[TT-EXECUTOR] REFUSE FOREGROUND_HOST_NOT_READY`. Both calls to `verify_parent_window` in the actual spawn wrapper precede `exec real-spawn.sh`; the latter is the entry to host_spawn. This is a wrapper foreground rejection, not evidence of a Toutiao child randomly exiting. The log does not identify which of the two checks refused, so that remains unknown.

`launch-common.sh.stdout` requires a unique imehost row with a nonnegative eighth field. The later saved WMS row has WID 29 and eighth field -1; its screenshot is a lock screen. These observations support foreground loss but do not timestamp the exact failing check.

The outer operator identified an execution-plan omission: T11 suppressed the previously documented awake override, permitting lock-screen interference (reported as 10 seconds). The preserved timeout record confirms **executed:false/device_rc:null**; this packet does not independently measure the timeout value. RUNBOOK lines 18/67 document the existing awake procedure. A future revision may temporarily override and restore the prior value. No such setting change occurred here, and the foreground guard must remain strict.

The three post-unlock reads have host rc0 and explicit T11_READ_RC=0, with boot bookends. Original failed launch, screenshots, guardian state, and packet remain untouched. Archive revision 02 adds these receipts; archive 01 and its rc255 upload failure are retained.
