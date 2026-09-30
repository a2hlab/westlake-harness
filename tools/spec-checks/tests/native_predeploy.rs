use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("scripts/lab/native_predeploy_tests.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline native gate tests");
    assert!(status.success());
}

#[test]
fn native_predeploy_initialization() {
    run("InitializationTests");
}

#[test]
fn native_predeploy_identity() {
    run("IdentityTests");
}

#[test]
fn native_predeploy_exceptions() {
    run("ExceptionTests");
}

#[test]
fn native_predeploy_needed() {
    run("NeededTests");
}

#[test]
fn native_predeploy_replay() {
    run("ReplayTests");
}

#[test]
fn native_predeploy_fail_closed() {
    run("FailClosedTests");
}
