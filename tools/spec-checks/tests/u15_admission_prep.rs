use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-admission-prep/test_prep.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run cold U15 admission preparation checks");
    assert!(status.success());
}

#[test]
fn u15_admission_bindings() {
    check("--bindings");
}

#[test]
fn u15_admission_pair() {
    check("--pair");
}
