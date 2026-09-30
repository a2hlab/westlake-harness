use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u5-investigate/test_classify.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run PID-scoped U5 INVESTIGATE tests");
    assert!(status.success());
}

#[test]
fn investigate_pid_scope() {
    run("PidTests");
}

#[test]
fn investigate_cohort() {
    run("CohortTests");
}

#[test]
fn investigate_categories() {
    run("CategoryTests");
}

#[test]
fn investigate_false_markers() {
    run("MarkerTests");
}

#[test]
fn investigate_benign_support() {
    run("BenignSupportTests");
}

#[test]
fn investigate_benign_safety() {
    run("BenignSafetyTests");
}
