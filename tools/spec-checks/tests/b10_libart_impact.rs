use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-b10-libart-impact/test_impact.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline libart impact checks");
    assert!(status.success());
}

#[test]
fn b10_libart_identity() {
    check("IdentityTests");
}

#[test]
fn b10_libart_classes() {
    check("ClassTests");
}

#[test]
fn b10_libart_bitvector() {
    check("BitVectorTests");
}

#[test]
fn b10_libart_runs() {
    check("RunTests");
}
