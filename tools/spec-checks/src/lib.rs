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
fn b6_wikipedia_lit() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "wikipedia"]);
}

#[test]
fn b6_caller_identified() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "caller"]);
}

#[test]
fn b6_no_regression_helloworld_zigzag() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "regression"]);
}

#[test]
fn b6_next_wall_recorded() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "nextwall"]);
}

#[test]
fn b6_fix_absent_detected() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "negative"]);
}

#[test]
fn b6_null_check_mode_recorded() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "null"]);
}

#[test]
fn b6_sigchain_exports_cover_libart_imports() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "symbols"]);
}

#[test]
fn b6_generation_passes_identity_gate() {
    run(&["benchmark/2026-09-28-bms-route-deploy/latest-source-generation/verify.py", "identity"]);
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
fn b9_single_bridge_swap_accepted() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "swap"]);
}

#[test]
fn b9_bridge_exports_manifest_jni() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "exports"]);
}

#[test]
fn b9_custom_application_created() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "application"]);
}

#[test]
fn b9_bridge_build_fails_on_missing_source() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "missing"]);
}

#[test]
fn b9_no_regression() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "regression"]);
}

#[test]
fn b9_deploy_tool_rejects_mismatch() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "mismatch"]);
}

#[test]
fn b9_rollback_on_failed_deploy() {
    run(&["benchmark/2026-09-29-unlocked-generation/verify.py", "rollback"]);
}

#[test]
fn n1_frozen_sources_and_package() {
    run(&["benchmark/2026-09-30-n1-native/verify.py", "frozen"]);
}

#[test]
fn n1_cluster_dispositions() {
    run(&["benchmark/2026-09-30-n1-native/verify.py", "clusters"]);
}

#[test]
fn n1_host_closure_and_negative() {
    run(&["benchmark/2026-09-30-n1-native/verify.py", "host"]);
}

#[test]
fn n1_device_evidence() {
    run(&["benchmark/2026-09-30-n1-native/verify.py", "device"]);
}

#[test]
fn n1_rollback_handoff() {
    run(&["benchmark/2026-09-30-n1-native/verify.py", "handoff"]);
}

#[test]
fn n2_sources_and_predictions() {
    run(&["benchmark/2026-09-30-n2-native/verify.py", "sources"]);
}
#[test]
fn n2_namespace_and_abi() {
    run(&["benchmark/2026-09-30-n2-native/verify.py", "namespace"]);
}
#[test]
fn n2_package_and_frozen() {
    run(&["benchmark/2026-09-30-n2-native/verify.py", "package"]);
}
#[test]
fn n2_handoff() {
    run(&["benchmark/2026-09-30-n2-native/verify.py", "handoff"]);
}

#[test]
fn n3_cluster_sources() {
    run(&["benchmark/2026-09-30-n3-native/verify.py", "sources"]);
}

#[test]
fn n3_jni_and_domains() {
    run(&["benchmark/2026-09-30-n3-native/verify.py", "namespace"]);
}

#[test]
fn n3_package_frozen() {
    run(&["benchmark/2026-09-30-n3-native/verify.py", "package"]);
}

#[test]
fn n3_handoff() {
    run(&["benchmark/2026-09-30-n3-native/verify.py", "handoff"]);
}

#[test]
fn n3_device_baseline() {
    run(&["benchmark/2026-09-30-n3-61b/verify.py", "baseline"]);
}

#[test]
fn n3_device_evidence() {
    run(&["benchmark/2026-09-30-n3-61b/verify.py", "evidence"]);
}

#[test]
fn n3_device_restored() {
    run(&["benchmark/2026-09-30-n3-61b/verify.py", "restored"]);
}

#[test]
fn n3b_publication_host() {
    run(&["benchmark/2026-09-30-n3b-webview/verify.py", "host"]);
}

#[test]
fn n3b_single_runtime_package() {
    run(&["benchmark/2026-09-30-n3b-webview/verify.py", "package"]);
}

#[test]
fn n3b_java_handoff() {
    run(&["benchmark/2026-09-30-n3b-webview/verify.py", "handoff"]);
}
