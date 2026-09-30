use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u6-scoring/test_score.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run evidence-bound U6 scoring tests");
    assert!(status.success());
}

#[test]
fn u6_scoring_noise_support() {
    run("NoiseSupportTests");
}

#[test]
fn u6_scoring_noise_safety() {
    run("NoiseSafetyTests");
}

#[test]
fn u6_scoring_intake() {
    run("IntakeTests");
}

#[test]
fn u6_scoring_axes() {
    run("AxesTests");
}

fn fatal(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u6-scoring/test_first_fatal.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run termination-first known answers");
    assert!(status.success());
}

#[test]
fn u6_scoring_first_fatal_answers() {
    fatal("KnownAnswerTests");
}

#[test]
fn u6_scoring_first_fatal_boundaries() {
    fatal("BoundaryTests");
}

fn measured(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u6-scoring/test_measured.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("replay signed U6 observations");
    assert!(status.success());
}

#[test]
fn u6_scoring_measured_intake() {
    measured("MeasuredIntakeTests");
}

#[test]
fn u6_scoring_measured_replay() {
    measured("MeasuredReplayTests");
}
