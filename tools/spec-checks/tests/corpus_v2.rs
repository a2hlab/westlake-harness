use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-corpus-v2/test_selection.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run corpus-v2 selection checks");
    assert!(status.success());
}

#[test]
fn corpus_v2_identity() {
    check("IdentityTests");
}

#[test]
fn corpus_v2_rejection() {
    check("RejectionTests");
}

#[test]
fn corpus_v2_prediction() {
    check("PredictionTests");
}

#[test]
fn corpus_v2_replay() {
    check("ReplayTests");
}
