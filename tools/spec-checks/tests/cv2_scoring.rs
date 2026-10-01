use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-cv2-scoring/test_score.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run corpus-v2 signed scoring checks");
    assert!(status.success());
}

#[test]
fn cv2_scoring_identity() {
    check("IdentityTests");
}

#[test]
fn cv2_scoring_confusion() {
    check("ConfusionTests");
}

#[test]
fn cv2_scoring_feedback() {
    check("FeedbackTests");
}

#[test]
fn cv2_scoring_replay() {
    check("ReplayTests");
}
