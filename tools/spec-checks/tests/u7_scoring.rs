use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u7-scoring/test_score.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U7 preliminary scoring tests");
    assert!(status.success());
}

#[test]
fn u7_scoring_identity() {
    run("IdentityTests");
}

#[test]
fn u7_scoring_attempts() {
    run("AttemptTests");
}

#[test]
fn u7_scoring_axes() {
    run("AxisTests");
}

#[test]
fn u7_scoring_replay() {
    run("ReplayTests");
}
