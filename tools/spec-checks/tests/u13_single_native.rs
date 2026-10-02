use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u13-single-native/test_analysis.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run offline U13 single-variable checks");
    assert!(status.success());
}

#[test]
fn u13_single_native_policy() {
    run_part("policy");
}

#[test]
fn u13_single_native_route() {
    run_part("route");
}

#[test]
fn u13_single_native_evidence() {
    run_part("evidence");
}
