# Outer acceptance: compile evidence only

The first wrapper could overwrite logs, delayed the baseline gate and used a personal compiler path. The second wrapper still used removable assertions and mishandled relative output paths and process-start errors. These were repaired before acceptance. Early negative tests exercised only their assertion helper; final tests now invoke the production checker or driver against modified disposable copies.

Outer verified **28 original build records**, all four actual VM command return codes (all0), the baseline ABC **bb1eccd3 (3244 bytes)** and two identical candidate ABCs **db781436 (6644 bytes)**. Raw originals and ABCs are additionally backed up under `$HOME/.local/share/westlake/t40-outer-20261022/raw-v3` outside the author worktree. `raw-intake.json` records that intake.

Outer independently copied the14-path frozen package, checked12 manifest hashes, and reran the real evidence checker plus **six production-path negative cases**, all passing. Author inputs remained unchanged during copying and execution. `verify-receipt.json` binds that execution; the original stdout/stderr remain in the persistent outer directory, and the public result replaces only the disposable test path. No compiler or device was run during this outer replay.

The independent Codex reviewer statically rechecked script SHA `9def16f56390178ffb22626f1f1fc47a56b8cc174069985f5456bc3a779e616d`: explicit checks survive optimization, output is resolved before VM commands, OSError records rc/time/error separately, and original stderr remains untouched. Static timeout presence does not prove remote termination under every failure.

Process deviations remain visible. The author made intermediate commit `e39c00cf663ffcf202d2b010c74204c38fd0340c` despite this card requiring path-only delivery; it contains an earlier checker and is **not the accepted final version**. Final acceptance is by the delivered SHA manifest, without rewriting author history. The broad VM search deviation is recorded in the author's evidence file.

This accepts reproducible source compilation, not a signed HAP, deployment, manual click qualification, white-screen repair or game acceptance. The API freeze table is unchanged. The whole-repository user-path check has a previously recorded unrelated violation in the October14 source-closeout verifier; scoped gates must not be described as a global clean result.
