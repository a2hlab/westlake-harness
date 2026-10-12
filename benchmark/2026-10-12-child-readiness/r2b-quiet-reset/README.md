# Quiet reset revision (r2b)

R2 accepted an inherited `RB_AUDIT_QUIET=1`, suppressing target failure diagnostics. This independent revision resets that flag to zero when the helper is sourced. Only the discovery subshell subsequently opts into quiet mode. All identity checks remain unchanged; the old r2 and earlier frozen candidates are untouched.

`evidence/tests.stderr.txt` records 11 passing tests: the original ten plus the inherited-flag negative regression. The actual r2 function reproduces rc1 with empty stderr; the new function returns rc1 and the exact UID failure JSON despite an inherited/exported quiet flag. Discovery still performs zero `od` calls and returns the same PID set, while target diagnostics remain active.

Helper, entry, members, startup, and startup.expected.sha256 are refreshed together. Watchdog, readiness worker, launch-common, and compose are byte-identical to r2. Compose still requires the existing worker's exact PRESENT preimage and preserves actual startup values. Candidate startup is a disabled template; this directory grants no execution authority. No device, VM, remote, signal, or data operations were performed.

Run `python3 benchmark/2026-10-12-child-readiness/r2b-quiet-reset/test_quiet_scan.py`. Exact file hashes are in checkpoint-manifest.json. Outer binds the fresh 24-member plan and current preimages independently.
