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
