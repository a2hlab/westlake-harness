# R12: native debugger compatibility on an owned OH probe

R11 could attach but its SDK15 server asserted during the remote handshake and produced zero target events. This run tested the replacement on a disposable probe before returning to the application.

**Accepted only for probe tool compatibility.** On 5cd, SDK15 host `c6008509` and static NDK r23b server `13c0b4bf` completed two real hardware breakpoint hits at `0x557bae4af0`: TID 1610, x0 9 → 10, StopID 2 → 4. The observer deleted its breakpoint and detached. Independent HDC reads verified the same probe identity, TracerPid 0, state S and stdout counts 12 → 16.

The server had exited; the outer terminated only its exact owned probe (boot/PID/birth/executable SHA guarded). Forward removal returned rc0, the subsequent forwarding list and listening sockets were clear, and the board lock was released. No APK, runtime, system or network configuration changed. This does not establish compatibility with the application process or video playback.

The first read-only preflight encountered a shell wrapper trailing-newline syntax error; its raw output remains archived. The corrected invocation used a subshell and a fresh nonce. No write occurred in that failed preflight.

[Observation](observation.json), [raw hits](raw-hits.jsonl), [commands](commands.jsonl), [cleanup](cleanup.json), [original evidence index](private-source-index.json), and [remote archive receipt](archive-receipt.json) retain the audit trail. Probe source, exact payload and build recipe are in the parent directory; original build stdout/stderr/rc are in the archive. A new observer version must explicitly pin the validated server; R11 is unchanged.
