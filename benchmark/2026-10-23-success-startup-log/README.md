# T93 successful startup prefix: untimed stages, no optimization candidate

The application log's `No such file` message is not a transport failure. The original prefix has21154 bytes/300 lines, expected child6291 redirection header, rc0 and SHA `3eabb43d…`; these were checked offline. Outer supplied the empty-transport-stderr validation and corrected its original classifier without retry. No device action was performed by this review.

**Identity/time.** `boot.stdout:1` is the expected T87 boot. `head.stdout:22–23` explicitly identifies PID/TID6291 at10-23 17:22:00 (one-second precision); payload/session metadata is omitted from the public extract. This corroborates the T87 launch, but individual lines have no boot/birth identity. Neither filename nor mtime alone is used as proof. The later19:09:08 mtime is not a startup-stage timestamp; atime is not creation time.

**Observed order, not durations.** JNI registration reports38 ok/0 failed at82, startReg returns at150–151, adapter initialization completes at160, Java adapter checkpoints continue through242, direct launch is armed for Toutiao at243 and starts at256, ApplicationInfo is built at264, `ensureBindApplication` starts at265, and AppBindData is constructed at281. The300-line prefix ends during APK archive scanning. These stages lack their own time/PID fields and receive no elapsed-time attribution.

**Additional counters.** Lines251–255 contain raw `now=1427062/1427063` with TID6311 (one wake record uses6316). Unit and clock domain are not established by the allowed inputs; no conversion to trace seconds is claimed. T92's first child marker is `content::Start`, TID6311, uptime1461.881765 (trace2229), approximately17:22:35.31 using its accepted clock mapping. The PID wall anchor therefore precedes that marker by about35s; this is not a duration for any listed operation.

**Unknown / one gap.** No clock-bound stage start/end pair explains that interval, and the short prefix does not reach the whole feed startup. No specific source-bound API optimization is established. The `.dm`/`classes22.dex` lookup messages do not establish a latency or failure cause in this successful launch. No extra logs, source, exit/memory analysis or T91 action was requested or performed.

Raw input remains under `$HOME/.local/share/westlake/success-startup-log-20261023/`. Only allowlisted non-sensitive excerpts are exported in `results.json`. Reproduce: `python3 benchmark/2026-10-23-success-startup-log/extract_evidence.py --output /tmp/t93-results.json`.
