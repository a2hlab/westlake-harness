use std::path::PathBuf;
use std::process::Command;
fn check(names: &[&str]) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let script = root.join("benchmark/2026-10-20-5cd-owned-child-reentry/test_t13.py");
    let out = Command::new("python3").arg(script).args(names).current_dir(root).output().expect("offline Python regressions");
    assert!(out.status.success(), "{}\n{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
#[test] fn ttvideo_t13_adoption_refuses_drift() { check(&["Production.test_profile_syntax_preview", "Production.test_owned_identity_drift", "Production.test_main_reused_child_refuses", "Production.test_adopted_instance_guard"]); }
#[test] fn ttvideo_t13_adopts_without_spawn() { check(&["Production.test_main_adopts_real_branch", "Production.test_main_missing_child_no_fallback"]); }
#[test] fn ttvideo_t13_signal_exact_child() { check(&["Production.test_term_once_real_rb_signal", "Production.test_term_failure_receipt_lost_no_repeat", "Production.test_term_drift_zero_signal", "Production.test_term_identity_race_after_intent"]); }
#[test] fn ttvideo_t13_exit_classification() { check(&["Production.test_monitor_zombie_and_reuse", "Production.test_exit_absent_unknown_and_boot"]); }
// Mechanical prerequisite only. Real desktop/icon/feed remains human PendingReview.
#[test] fn ttvideo_t13_one_reentry() { check(&["Production.test_real_spawn_parent_shell_seq2", "Production.test_real_spawn_failure_sticky_intent", "Production.test_real_reentry_edge", "Production.test_owned_window_child_none"]); }
#[test] fn ttvideo_t13_stop_deadline() { check(&["Production.test_stop_deadline_before_spawn", "Production.test_stop_arriving_during_owner_scan", "Production.test_spawn_wrapper_guards_after_jit"]); }
// Preview/shell prerequisite only. Device power/guardian exit readbacks remain human PendingReview.
#[test] fn ttvideo_t13_cleanup() { check(&["Production.test_profile_syntax_preview", "Production.test_stop_deadline_before_spawn"]); }
