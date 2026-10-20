# T30 deployment peer review

The first observed draft retained only the old T29 slot reader self-pin. The current T30 reader has now been pinned at its actual new repository path and SHA; no runtime reader logic changed to close that finding.

The reviewed data consistently select shim `7f8d75bb…` (107,544 bytes), unchanged bridge `b0e5602a…`, and geometry offset `0xf8bc`. Lock/unlock remain `0x72c8/0x72dc`. All eight admission self-pins, original executor `693448c2…`, seven exact copied files and the first five transaction artifacts match. The public production receipt equals the original receipt semantically. Fresh identity, approval, metadata and live-slot fields remain unfilled.

An independent run of the actual helper checker passed 16 cases, including unsigned preflight/apply/rollback rejection before Board construction, original apply-plan binding, default no-transport behavior, phase budgets, source equality and the current reader self-pin. No device command or production rebuild was performed. Fresh admission parsing was source-reviewed for bookended identity/file checks and current-window receipt dates; it was not represented as a live admission observation.

This package reviews the exact observed source hashes. The author final commit was pending at publication; a final landing review must compare its bytes against `source-pins.json`. These offline results do not grant device authorization or establish video recovery. Private snapshots retain the original missing-pin draft and subsequent correction without overwriting history.
