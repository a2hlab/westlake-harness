use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u7-prospective/v1/test_predict.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("verify frozen U7 composition and forecast");
    assert!(status.success());
}

#[test]
fn u7_final_candidate() {
    run("CandidateTests");
}

#[test]
fn u7_final_inputs() {
    run("InputTests");
}

#[test]
fn u7_final_predictions() {
    run("PredictionTests");
}

#[test]
fn u7_final_freeze() {
    run("FreezeTests");
}
