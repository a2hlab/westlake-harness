# G23 shell heredoc status — minimal handoff

`Board.raw_shell` appended `; bms_rc=...` to the heredoc closing line. Use a newline separator so the delimiter remains on its own line; rc capture, marker validation, read-only retry count/deadline and no-write-replay policy are unchanged. Production diff is one changed expression plus its explanatory comment. Main source/test hashes matched this worktree before editing; see `pins.json` and `minimal.patch`.

Actual offline results: original `test_bms_batch` **70/70 PASS**, including five new tests executing the production wrapper via real local `/bin/sh`. The original Rust `bms_batch_offline` selector ran **98 Python tests, one existing plan/runner hash-drift error**, rc101. This pin was not changed or bypassed. Exact failure is preserved in `rust-selector.stderr.txt`; all command rc/stdout/stderr are in `commands.json`. The first full-suite attempt's shared-lock PermissionError is also retained; the successful offline suite used the original BMS_BATCH_LOCK_DIR option pointing to an isolated temporary test directory.

Reproduce from repo root with BMS_BATCH_LOCK_DIR set to an isolated disposable test directory: `python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p test_bms_batch.py -v`. Original Rust selector: `cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --lib bms_batch_offline -- --exact --nocapture` (same isolated test-lock setting; reports the preserved stale plan pin).

The real G21 command-01384 stdout (`/bin/sh: here document 'LABEL_RECIPE_INPUT' unclosed`) and argv are retained with original hashes. They were not executed locally; new tests use its heredoc/`-- apply -` shape with inert stdin echoing. No label recipe, gate, permission, runtime or device was changed. No commit/push attempted.

Outer has independently reported the five new cases PASS. Land only after original apply termination; current window is **same-journal original rollback only**, no candidate retry. t23's human/device rollback acceptance remains with outer. `landing-paths.txt` includes the two authorized source/test files and this evidence only.
