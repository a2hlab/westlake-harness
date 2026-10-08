use std::path::Path;
use std::process::Command;

#[test]
fn u14_stage_a_decision_draft() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-08-u14-stage-a-decision-draft/test_decision.py"))
        .current_dir(root)
        .status()
        .expect("run unsigned U14 decision known answers");
    assert!(status.success());
}
