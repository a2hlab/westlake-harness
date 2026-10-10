# Pre-window checklist + static-triptych as GATES (cc-t3 #91, RUNBOOK bd1d5baa30)

Three auto-checkable gates from the RUNBOOK '开窗前检查表' + '静态三件套'. All offline, fail-closed, tested.

## ① board_state_diff.py — plan-scope comparability
If `plan_sha256` differs between reference and subject, or either side is empty, the PATH-SET fields
(`labels`, `sha`, `bind_targets`) are reported `status: NOT-COMPARABLE` instead of per-path `absent`
("missing"). A path present in one scope and absent in the other is scope, not drift. Exit codes:
0 comparable, 1 incomplete/drifted, 2 refuse (bad input), **3 NOT-COMPARABLE (plan mismatch)**.
Known answer (today's real misjudgement): `westlake-harness-tools-inventory/benchmark/2026-10-10-5ea-u13-restore/v2/post-reboot-pre-app/snapshot.json`
(plan_sha256 6eb5177d) vs `benchmark/2026-10-10-5ea-revive/snapshot-1853/snapshot.json` (plan_sha256 None):
old reported 27 route-a "missing"; new reports NOT-COMPARABLE (exit 3, zero route-a leaks). Observed
non-path-set fields (scalars/params/pids/init_configs/mounts/raw) still diff. Tests: test_board_state 17/17.

## ② scripts/lab/window_preflight.py — read-only pre-window gate (NEW)
`window_preflight.py <serial> --keys k1,.. --control <key> --baseline <dir> --manifest <m.json> [--launch icon-tap] [--hdc hdc]`
Per-item PASS/FAIL; any FAIL -> non-zero:
- `selinux-mode`: `getenforce` == the baseline's recorded SELinux mode; baseline with no recorded mode -> FAIL "baseline mode unknown".
- `clean-boot`: uptime <= threshold AND none of the keys'/control's packages already started since boot (WMS conflict risk, reported).
- `manifest+bms`: every key and control is in the batch manifest AND BMS-queryable (`bm dump -a`).
- `launch-method`: the intended launch method == the baseline's recorded method.
Pure read-only; board ops go through `--hdc` so it is testable with a fake. Tests: test_window_preflight 7/7.

## ③ signoff missing SELinux mode -> refuse
A permissive-captured baseline must never be compared as Enforcing. If the signoff/reference has no
`selinux_mode`:
- `regress_vs_signoff.py` refuses unless `--selinux-mode "enforcing|permissive;<source-evidence>"` backfills it (recorded in the report).
- `demo_seal_61b.py validate()` refuses unless the plan sets `selinux_mode_source` citing evidence (e.g. "permissive; benchmark/2026-09-30-board-inventory/61b/misc.txt"); plan-template declares the default source.
Tests: test_regress_vs_signoff 19/19 (SignoffSelinuxModeGate), test_selinux_mode_switch 15/15.

All: check_user_paths 0, check_frozen 0 (no frozen item touched).
