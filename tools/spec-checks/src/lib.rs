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
