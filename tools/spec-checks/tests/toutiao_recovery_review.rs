use std::path::Path;
use std::process::Command;

fn run_review_suite(suite: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("test_review.py")
        .arg(suite)
        .arg("-v")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root.join("benchmark/2026-10-12-toutiao-recovery-review"))
        .status()
        .expect("run offline Route B recovery review tests");
    assert!(status.success(), "Route B review suite failed: {suite}");
}

#[test]
fn toutiao_recovery_review_evidence() {
    run_review_suite("EvidenceTests");
}

#[test]
fn toutiao_recovery_review_preview() {
    run_review_suite("PreviewTests");
}

#[test]
fn toutiao_recovery_review_candidate() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("test_final_receipts.py")
        .arg("-v")
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root.join("benchmark/2026-10-12-toutiao-recovery-review"))
        .status()
        .expect("verify independent final candidate receipts without rerunning accepted suites");
    assert!(status.success());
}
