# T0 collection experiment: blocked at installed-host identity

The old assumption was wrong: a valid `framework-2` report does not establish the installed host identity. The first control probe rejected the host before spawning a child. **1 attempted control, 0 child launches, 0 screenshots, 0/43 blocked-app observations.** No app regression or app root cause is inferred.

The new rule is to verify the installed host HAP alongside framework and boot hashes before interpreting a control run. The outer loop must restore or explicitly select the matching signed host before another minimal experiment.

| Host artifact | SHA-256 |
|---|---|
| Signed build record and local HAP | `8cfa5bb1eb1a26fa69dbfd5618cecf0aefb282f6035aa9af24dcb9f96eb81267` |
| Installed HAP on 5ea | `df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a` |

Evidence: [probe failure](evidence/probe-failure.txt), [probe's actual host hash command](evidence/host-check.json), [original attempt](evidence/attempt-original.json), [results](results.json). The original attempt reports a missing device-report file because the first collector revision read it before checking the probe exit code. The collector now preserves the actual probe failure. That reporting fix has not been rerun on the board.

Run identity: `cx10-20260928-1625`, serial `5ea34a4500000000000000001123012c`. Full VM artifacts remain at `~/a2hlab/ws/out-appsweep-t0-cx10-20260928-1625/`. The framework file inventory is archived in [framework.json](evidence/framework.json); its historical `passed` field is not a current board acceptance. No screenshot paths exist because snapshot collection was never reached.

The board lock was reacquired after the outer loop fixed its process lifetime, and `held` confirmed cx-t0 before writes. Preflight found no appspawn/broker/keeper processes. The only collector writes before the probe gate were host force-stop, appspawn stop (no matching process), and the screen timeout. The probe read and verified framework hashes, read host metadata and checked the installed HAP, then stopped. No host install, runtime/framework/APK modification, directory cleanup, SIGQUIT, or other-board command occurred. The lock was released after read-only hash verification.

## Implementation and limits

`t0_minexp.sh` now calls `t0_collect.py`, restricted to Wikipedia and markor on 5ea. It uses a new OUT_ROOT and app-input copy; checks lock ownership and attachment between phases; selects stderr by the report's exact runtime and PID; keeps raw and filtered line counts; filters epoch-formatted hilog by PID/time; uses unique screenshots; and attempts two bounded SIGQUIT captures regardless of render nodes. The post-launch paths remain **unverified**, because the probe failed before reaching them. Render-node binding is explicitly unresolved. ART dump destination/completion, normal Looper identification, full board hash stability, shard recovery/merging and the 43-key inventory remain incomplete. The legacy script's automatic LIT branch was removed; that script still lacks T0 safeguards and must not be used for new sweeps.

Only an interrupted Wikipedia attempt exists. It is retained, excluded from effective records, and cannot be replaced by old verdicts. Markor and the batch are not-run. No cross-board attempt selection is implemented or claimed. Shared Wikipedia app-input metadata matched the copied metadata after failure; full cross-lane before/after inventories were not completed.

## Validation

R2: **partially**. Installed-host mismatch is verified by the probe and an independent read-only hash. Board forensics and visual outcomes are unverified. Repository baseline: 69 tests run, 67 passed, 2 skipped.

Two Rust selectors call the production Python filter. Synthetic logs cover own PID, foreign PID, command self-match, old time and future time. Real production mutations (`PID check -> True` and `time window -> True`) each make the filter assertion fail. These are offline negative controls; no real child crash log was collected. The 12 missing selectors are reported as skip, not success. Full task completion is not claimed and the contract was not modified.

`agent-spec lifecycle specs/app-lighting/t0-sweep-forensics.spec.md --code tools/spec-checks --format json`: exit 1, 2 pass / 12 skip. [Full report](evidence/lifecycle.json).

| Selector | Verdict |
|---|---|
| `t0_blocked_apps_have_observations` | skip |
| `t0_pure_jvm_apps_have_main_stack` | skip |
| `t0_stack_timeout_marked_capture_failed` | skip |
| `t0_hilog_keeps_own_pid_crash_only` | pass |
| `t0_stderr_located_by_pid` | skip |
| `t0_stale_screenshot_rejected` | skip |
| `t0_lit_control_set_unchanged` | skip |
| `t0_board_without_full_lit_control_excluded` | skip |
| `t0_lock_contention_no_writes` | skip |
| `t0_midrun_detach_stops_shard` | skip |
| `t0_merged_triage_one_record_per_app` | skip |
| `t0_isolated_out_root` | skip |
| `t0_cleanup_exempts_toutiao_dirs` | skip |
| `t0_negative_controls_fail` | pass |
