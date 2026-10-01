use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u8-prospective/batch-v2/test_batches.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U8 two-layer batch checks");
    assert!(status.success());
}

#[test]
fn u8_batches_donors() {
    check("DonorTests");
}

#[test]
fn u8_batches_coverage() {
    check("CoverageTests");
}

#[test]
fn u8_batches_replay() {
    check("ReplayTests");
}
