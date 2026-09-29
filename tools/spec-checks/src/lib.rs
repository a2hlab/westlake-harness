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
fn board_parity_offline() {
    run(&["-m", "unittest", "discover", "-s", "benchmark/2026-09-29-board-parity", "-p", "test_*.py"]);
}

#[test]
fn board_parity_live_evidence() {
    run(&["benchmark/2026-09-29-board-parity/verify_live.py"]);
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
fn b77_pinned_inputs_and_causes() {
    run(&["benchmark/2026-09-29-install-walls/test_walls.py", "Walls.test_inputs"]);
}

#[test]
fn b77_candidate_patch_regressions() {
    run(&["benchmark/2026-09-29-install-walls/test_walls.py", "Walls.test_candidate"]);
}

#[test]
fn b77_impact_and_provenance() {
    run(&["benchmark/2026-09-29-install-walls/test_walls.py", "Walls.test_impact"]);
}
