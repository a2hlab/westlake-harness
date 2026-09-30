use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u5-feedback-v1/test_feedback.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline U5 static feedback tests");
    assert!(status.success());
}

#[test]
fn u5_feedback_rules() {
    run("RuleTests");
}

#[test]
fn u5_feedback_coverage() {
    run("CoverageTests");
}

#[test]
fn u5_feedback_inputs() {
    run("InputTests");
}

#[test]
fn u5_feedback_version() {
    run("VersionTests");
}
