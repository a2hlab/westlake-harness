#[cfg(test)]
mod tests {
    fn check(name: &str) {
        let status = std::process::Command::new("python3")
            .arg(concat!(env!("CARGO_MANIFEST_DIR"), "/checks/t0_checks.py"))
            .arg(name)
            .status()
            .expect("start production collector checks");
        assert!(status.success(), "{name} failed");
    }
    #[test]
    fn t0_blocked_apps_have_observations() { check("t0_blocked_apps_have_observations"); }
    #[test]
    fn t0_pure_jvm_apps_have_main_stack() { check("t0_pure_jvm_apps_have_main_stack"); }
    #[test]
    fn t0_stack_timeout_marked_capture_failed() { check("t0_stack_timeout_marked_capture_failed"); }
    #[test]
    fn t0_hilog_keeps_own_pid_crash_only() { check("t0_hilog_keeps_own_pid_crash_only"); }
    #[test]
    fn t0_stderr_located_by_pid() { check("t0_stderr_located_by_pid"); }
    #[test]
    fn t0_stale_screenshot_rejected() { check("t0_stale_screenshot_rejected"); }
    #[test]
    fn t0_lit_control_set_unchanged() { check("t0_lit_control_set_unchanged"); }
    #[test]
    fn t0_board_without_full_lit_control_excluded() { check("t0_board_without_full_lit_control_excluded"); }
    #[test]
    fn t0_lock_contention_no_writes() { check("t0_lock_contention_no_writes"); }
    #[test]
    fn t0_midrun_detach_stops_shard() { check("t0_midrun_detach_stops_shard"); }
    #[test]
    fn t0_merged_triage_one_record_per_app() { check("t0_merged_triage_one_record_per_app"); }
    #[test]
    fn t0_isolated_out_root() { check("t0_isolated_out_root"); }
    #[test]
    fn t0_cleanup_exempts_toutiao_dirs() { check("t0_cleanup_exempts_toutiao_dirs"); }
    #[test]
    fn t0_negative_controls_fail() { check("t0_negative_controls_fail"); }
}
