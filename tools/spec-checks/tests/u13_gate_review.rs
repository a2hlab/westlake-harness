use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u13-gate-review/test_review.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run U13 pending review checks");
    assert!(status.success());
}

#[test]
fn u13_gate_review_proof() {
    run_part("proof");
}

#[test]
fn u13_gate_review_drafts() {
    run_part("drafts");
}
