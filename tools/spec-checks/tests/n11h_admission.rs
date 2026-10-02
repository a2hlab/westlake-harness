use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-n11h-admission/test_admission.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline N11h admission checks");
    assert!(status.success());
}

#[test]
fn n11h_admission_timing() {
    check("TimingTests");
}

#[test]
fn n11h_admission_smoke() {
    check("SmokeTests");
}

#[test]
fn n11h_admission_strings() {
    check("StringsTests");
}

#[test]
fn n11h_admission_exceptions() {
    check("ExceptionsTests");
}
