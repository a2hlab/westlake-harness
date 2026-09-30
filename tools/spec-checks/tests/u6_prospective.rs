use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u6-prospective/test_forecast.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline U6 prospective tests");
    assert!(status.success());
}

#[test]
fn u6_input_identity() {
    run("InputTests");
}

#[test]
fn u6_candidate_identity() {
    run("CandidateTests");
}

#[test]
fn u6_forecast_coverage() {
    run("CoverageTests");
}

#[test]
fn u6_freeze_and_scoring() {
    run("FreezeTests");
}
