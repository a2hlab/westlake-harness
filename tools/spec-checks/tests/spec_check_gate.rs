use std::path::Path;
use std::process::Command;

fn check(case: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .args(["scripts/lab/test_spec_checks.py", case])
        .current_dir(root)
        .status()
        .expect("run fake-Cargo gate checks");
    assert!(status.success());
}

#[test]
fn spec_gate_approved_failures() {
    check("GateTests.test_approved_failures");
}

#[test]
fn spec_gate_new_failure() {
    check("GateTests.test_new_failure");
}

#[test]
fn spec_gate_stale_exception() {
    check("GateTests.test_stale_exception");
}
