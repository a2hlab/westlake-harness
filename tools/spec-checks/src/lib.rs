fn run(args: &[&str]) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = std::process::Command::new("python3").args(args)
        .current_dir(root).status().expect("run evidence check");
    assert!(status.success());
}
#[test]
fn bms_batch_offline() {
    run(&["-m", "unittest", "discover", "-s", "benchmark/2026-09-28-bms-route-deploy/batch", "-p", "test_*.py"]);
}
#[test]
fn bms_batch_evidence() {
    run(&["benchmark/2026-09-28-bms-route-deploy/verify_batch_results.py"]);
}

#[test]
fn bms_spawn_ab_evidence() {
    run(&["benchmark/2026-09-28-bms-route-deploy/spawn-ab/verify.py"]);
}

#[test]
fn b1_wikipedia_lit_after_sandbox_prep() {
    run(&["benchmark/2026-09-28-bms-route-deploy/sandbox-prep/verify.py", "wikipedia"]);
}
#[test]
fn b1_sandbox_roots_match_helloworld() {
    run(&["benchmark/2026-09-28-bms-route-deploy/sandbox-prep/verify.py", "roots"]);
}
#[test]
fn b1_prep_failure_skips_launch() {
    run(&["-m", "unittest", "discover", "-s", "benchmark/2026-09-28-bms-route-deploy/batch", "-p", "test_bms_batch.py", "-k", "test_sandbox_failure_prevents_launch"]);
}
#[test]
fn b1_prep_is_idempotent() {
    run(&["benchmark/2026-09-28-bms-route-deploy/sandbox-prep/verify.py", "idempotent"]);
}

#[test]
fn b5_wikipedia_lit() {
    run(&["benchmark/2026-09-28-bms-route-deploy/alias-entry/verify.py", "wikipedia"]);
}

#[test]
fn b5_alias_resolved_to_target() {
    run(&["benchmark/2026-09-28-bms-route-deploy/alias-entry/verify.py", "alias"]);
}

#[test]
fn b5_non_alias_entry_unchanged() {
    run(&["benchmark/2026-09-28-bms-route-deploy/alias-entry/verify.py", "ordinary"]);
}

#[test]
fn b5_missing_target_reported() {
    run(&["benchmark/2026-09-28-bms-route-deploy/alias-entry/verify.py", "negative"]);
}

#[test]
fn bms_route_study_evidence() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = std::process::Command::new("python3")
        .arg(root.join("benchmark/2026-09-28-bms-route-study/verify.py"))
        .current_dir(&root)
        .status()
        .expect("run BMS evidence checks");
    assert!(status.success(), "BMS handoff evidence did not validate");
}

#[test]
fn b6_static_diff() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = std::process::Command::new("python3")
        .arg(root.join("benchmark/2026-09-29-b6-static-diff/verify.py"))
        .current_dir(&root)
        .status()
        .expect("run offline B6 ELF evidence and normalization checks");
    assert!(status.success(), "B6 static comparison evidence failed");
}

#[test]
fn b7_first_cause_recorded() {
    run(&["benchmark/2026-09-29-bms-link-entry-walls/verify.py", "first_cause"]);
}
#[test]
fn b7_wall_crossed() {
    run(&["benchmark/2026-09-29-bms-link-entry-walls/verify.py", "wall_crossed"]);
}
#[test]
fn b7_lit_by_outer_review() {
    run(&["benchmark/2026-09-29-bms-link-entry-walls/verify.py", "lit"]);
}
#[test]
fn b7_no_regression() {
    run(&["benchmark/2026-09-29-bms-link-entry-walls/verify.py", "no_regression"]);
}
#[test]
fn b7_blocked_reason_recorded() {
    run(&["benchmark/2026-09-29-bms-link-entry-walls/verify.py", "blocked"]);
}

#[test]
fn bms_rerun_offline() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = std::process::Command::new("python3")
        .args(["-m", "unittest", "discover", "-s", "benchmark/2026-09-28-bms-route-deploy/batch", "-p", "test_b4_rerun.py"])
        .current_dir(&root)
        .status()
        .expect("run three-shard FakeBoard plans and offline v4 aggregation checks");
    assert!(status.success(), "B4 rerun preparation checks failed");
}

#[test]
fn white_window_offline() {
    run(&["-m", "unittest", "discover", "-s", "benchmark/2026-09-29-white-window", "-p", "test_*.py"]);
}

#[test]
fn ability_stage_offline() {
    run(&["-m", "unittest", "discover", "-s", "benchmark/2026-09-29-white-window", "-p", "test_ability_stage.py"]);
}

#[test]
fn d4b_reference_and_receipt() {
    run(&["benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py", "ReferenceTests"]);
}

#[test]
fn d4b_t5b_artifact() {
    run(&["benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py", "T5bTests"]);
}

#[test]
fn d4b_mismatch_rejection() {
    run(&["benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py", "MismatchTests"]);
}

#[test]
fn d4b_unknown_review() {
    run(&["benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py", "UnknownTests"]);
}

#[test]
fn d4b_cli_integrity() {
    run(&["benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py", "IntegrityTests"]);
}
#[test]
fn b10_jni_matrix_known_answers() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_jni_matrix_known_answers"]);
}

#[test]
fn b10_jni_gate_blocks_new_missing() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_jni_gate_blocks_new_missing"]);
}

#[test]
fn b10_unknown_marked_not_guessed() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_unknown_marked_not_guessed"]);
}

#[test]
fn b10_service_matrix_known_gaps() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_service_matrix_known_gaps"]);
}

#[test]
fn b10_prediction_backtest() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_prediction_backtest"]);
}

#[test]
fn b10_build_silent_skip_fails() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_build_silent_skip_fails"]);
}

#[test]
fn b10_startup_reachability() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_startup_reachability"]);
}

#[test]
fn b10_typeface_exception_is_candidate() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_static.py", "StaticTests.test_typeface_exception_is_candidate"]);
}

#[test]
fn b10_v3_registration_ownership() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_v3.py", "V3Tests.test_registration"]);
}

#[test]
fn b10_v3_cache_and_exceptions() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_v3.py", "V3Tests.test_cache"]);
}

#[test]
fn b10_v3_risk_rules() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_v3.py", "V3Tests.test_risks"]);
}

#[test]
fn b10_v3_fatal_backtest() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_v3.py", "V3Tests.test_backtest"]);
}

#[test]
fn b10_v3_class_presence() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_classes_v3.py", "ClassesTests.test_presence"]);
}

#[test]
fn b10_v3_class_reachability() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_classes_v3.py", "ClassesTests.test_paths"]);
}

#[test]
fn b85_static_rules() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test85.py", "Task85Tests.test_rules"]);
}

#[test]
fn b85_prediction_freeze() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test85.py", "Task85Tests.test_freeze"]);
}

#[test]
fn b85_backtest_partition() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test85.py", "Task85Tests.test_backtest"]);
}

#[test]
fn b90_observations() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test90.py", "Task90Tests.test_observations"]);
}

#[test]
fn b90_network() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test90.py", "Task90Tests.test_network"]);
}

#[test]
fn b90_rankings() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test90.py", "Task90Tests.test_rankings"]);
}

#[test]
fn b90_batch_feedback() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_feedback90.py", "Feedback90Tests.test_batch"]);
}

#[test]
fn b90_feedback_rules() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_feedback90.py", "Feedback90Tests.test_rules"]);
}

#[test]
fn b90_feedback_coverage() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_feedback90.py", "Feedback90Tests.test_coverage"]);
}

#[test]
fn r16_prospective_freeze() {
    run(&["benchmark/2026-09-30-r16-prospective/test_prospective.py", "ProspectiveTests.test_freeze"]);
}

#[test]
fn r16_prospective_scoring() {
    run(&["benchmark/2026-09-30-r16-prospective/test_prospective.py", "ProspectiveTests.test_scoring"]);
}

#[test]
fn r16_feedback_rules() {
    run(&["benchmark/2026-09-30-r16-feedback/test_feedback.py", "FeedbackTests.test_rules"]);
}

#[test]
fn r16_feedback_matrix() {
    run(&["benchmark/2026-09-30-r16-feedback/test_feedback.py", "FeedbackTests.test_matrix"]);
}

#[test]
fn v2_feedback_rules() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_feedback_v2.py", "RuleTests"]);
}

#[test]
fn v2_feedback_matrix() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_feedback_v2.py", "MatrixTests"]);
}

#[test]
fn b10_installer_background() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_installer_background.py"]);
}

#[test]
fn b10_unified_r17r() {
    run(&["benchmark/2026-09-29-static-wall-prediction/test_unified_r17r.py"]);
}
