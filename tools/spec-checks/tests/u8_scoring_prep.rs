use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u8-scoring-prep/test_score.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline U8 scorer checks");
    assert!(status.success());
}

#[test]
fn u8_scoring_prep_identity() {
    check("IdentityTests");
}

#[test]
fn u8_scoring_prep_visual() {
    check("VisualTests");
}

#[test]
fn u8_scoring_prep_risks() {
    check("RiskTests");
}

#[test]
fn u8_scoring_prep_replay() {
    check("ReplayTests");
}
