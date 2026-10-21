# G21 window 01: restored baseline, game result still unknown

The original deployment reached 32 bound files and verified the candidate
hashes, but failed before service start. `Board.raw_shell` appended its status
suffix to the final heredoc delimiter in the original label recipe. The device
reported an unclosed heredoc; transport rc0 lacked the required remote marker.
This was a command-construction defect, not evidence of device disconnection.
No game launch occurred and no claim about the GLES wall is made.

The original automatic rollback restored all 32 overlays and the 319-target
baseline, then hit the same defect before its service start. Its terminal
`recovery_required` journal is preserved separately. G23's minimal newline fix
was independently reviewed and landed as `226d658b04`; the unchanged label
recipe and original same-journal rollback then returned rc0 / `rolled_back`.
The final journal retains the old failure strings; those are historical fields,
not a second failure of the successful explicit rollback.

The original label readback passed all 295 paths. Original U7 verified parent
21963, control child 22734 and its runtime maps. Outer then inspected
[the actual Hello World screenshot](control.jpeg), independently rehashed all
319 baseline targets, compared the full recorded mount stack, and verified the
three BoatAttack private library hashes. The control child was closed, no game
or control UID processes remained, and power returned to SLEEP with 30000 ms
timeout / 10000 ms override. [The desktop screenshot](desktop.jpeg) was also
visually inspected before restoring sleep.

The lock ran from 19:50:45 to 20:06:27.457 +08:00: **942.457 seconds**.
An actual `held` query returned rc1 with empty output after release. All 318
window-specific native exception rows were removed only after restoration;
the registry returned byte-for-byte to its pre-window hash. A future trial
needs a new bounded decision and fresh board checks.

`results.json`, `closure.json` and `window-closed.json` separate observed device
facts from the still-unknown game result. `original-evidence-index.json` pins
the complete original command streams and journals in persistent storage;
large stdout/stderr streams are not copied into git. The original first
failure, automatic-rollback failure, and successful explicit rollback remain
separate records. No runtime-success API entry or freeze is justified.

G23 validation: five real local shell cases and all 70 direct batch tests pass.
The broader Rust selector preserves a historical B4 runner-pin failure: the
plan pins `7c226d27`, whereas the pre-G23 source already hashed `f41efa6a`.
This older plan remains rejected; it was not repinned to hide a failing test.
