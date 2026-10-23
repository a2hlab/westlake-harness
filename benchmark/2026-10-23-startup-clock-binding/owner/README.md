# T94 owner: clock and deployed producer remain unknown

The raw `now=1427062/1427063` counters cannot be converted to milliseconds or aligned with trace time from their magnitude. No matching TOUCH21-POLL/WAKE implementation was found in the bounded local source/patch/build-script searches recorded in `results.json`.

Seven concrete MessageQueue source files from the main tree, vm-copies and00.Workspace are SHA-pinned in `evidence.json`; none contains either marker. The local T18 `touch21-source-header-check.json` describes950 source/header records for artifact `cf3c4308…`; its name does not bind these logs. The historical T80 receipt records `$RT/liboh_android_runtime.so` SHA `8ab6742d…` at `B/raw/B1_sha.stdout:13`, but no inspected evidence proves that artifact emitted the marker or connects it to an exact logging source.

**Single missing chain:** exact logging call/time expression and clock API → source SHA → producer output SHA → successful-child deployment evidence. API, unit and deployed clock domain remain **unknown**. T93 counters and T92 durations are unchanged; no guessed interval is added.

Reproduce the narrow pin/absence check: `python3 benchmark/2026-10-23-startup-clock-binding/owner/check_evidence.py --workspaces .. --output /tmp/t94-evidence.json`. This is not a claim of exhaustive filesystem absence. No device, deployment, REA, stopped-object analysis or remote access was performed. Public output contains only paths, hashes and non-sensitive metadata.
