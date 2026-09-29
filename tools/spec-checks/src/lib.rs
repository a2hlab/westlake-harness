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
fn b8_inventory_complete() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "inventory"]);
}
#[test]
fn b8_ported_fix_effective() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "effective"]);
}
#[test]
fn b8_white_window_advanced() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "white_window"]);
}
#[test]
fn b8_lit_by_outer_review() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "lit"]);
}
#[test]
fn b8_no_regression() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "no_regression"]);
}
#[test]
fn b8_not_ported_reason_recorded() {
    run(&["benchmark/2026-09-29-westlake-port/verify.py", "not_ported"]);
}
