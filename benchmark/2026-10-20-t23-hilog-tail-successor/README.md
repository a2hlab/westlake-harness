# PID-tail hilog successor (offline only)

The old `-x -z` combination returned transport/remote rc0 but printed `Mutlti commands can't be used in combination [CODE: -31]`. That capture is an error, not an empty successful log. The exact original fixture and device help are preserved with SHA pins. Old collectors and window evidence are unchanged.

Use `python3 hilog_tail.py plan --pid ACTUAL_PID --tail 2000` to obtain the shell fragment: `hilog -P ACTUAL_PID -z 2000 -L D,I,W,E,F -v epoch`. It uses only tail mode, no `-x`. This form is selected from actual help; this successor has not been run on a device. Outer runs it sequentially inside existing holder/boot/PID/birth guards, with an eight-second host timeout bounded by window time. Do not retry UI or introduce parallel HDC.

Persist stdout/stderr/transport rc verbatim, then use `inspect --stdout RAW --stderr ERR --transport-rc RC --pid ACTUAL_PID --postguard same|gone|unknown`. Missing completion, nonzero rc, nonzero `[CODE:]` or unexpected timestamped PID rejects the capture while retaining bytes. Child disappearance does not discard logs: postguard and PID reuse attribution remain explicit. The parser reports observed epoch first/last timestamps, matching line count and body bytes/SHA; empty/unparseable timestamps are unknown. Elapsed execution time is never coverage. Tail data does not prove complete action-time history. A proc guard's timestamps must stay outside the body markers.

Seven offline cases passed, including the actual rc0/-31 fixture. No device calls. Example PID7655 is historical, not a new admission.
