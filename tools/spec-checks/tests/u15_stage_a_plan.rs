use std::path::Path;
use std::process::Command;

#[test]
fn u15_stage_a_plan_draft() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-stage-a-plan/test_plans.py"))
        .current_dir(root)
        .status()
        .expect("run disabled U15 Stage A known answers without device IO");
    assert!(status.success());
}
