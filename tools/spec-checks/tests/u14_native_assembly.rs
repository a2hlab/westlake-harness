use std::path::Path;
use std::process::Command;

fn run_checks(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u14-native-assembly/test_assembly.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run disabled U14 draft checks without private artifacts");
    assert!(status.success());
}

#[test]
fn u14_native_assembly() {
    run_checks("--assembly");
}

#[test]
fn u14_native_static() {
    run_checks("--static");
}
