use std::path::PathBuf;
use std::process::Command;
fn run(names: &[&str]) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap();
    let mut cmd = Command::new("python3");
    cmd.arg("test_capture.py");
    for name in names { cmd.arg(format!("CaptureTests.{}", name)); }
    let output = cmd.current_dir(root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/capture61b-postinstall"))
        .env("PYTHONDONTWRITEBYTECODE", "1").output().expect("offline collector fixtures");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
#[test]
fn capture61b_preview() { run(&["test_delta_and_preview"]); }
#[test]
fn capture61b_complete() { run(&["test_complete_full_shape"]); }
#[test]
fn capture61b_identity_reject() { run(&["test_wrong_serial", "test_wrong_boot", "test_changed_bookend"]); }
#[test]
fn capture61b_content_reject() { run(&["test_stripped_cfg", "test_missing_uid", "test_remote_failure"]); }
#[test]
fn capture61b_root_reject() { run(&["test_root_present"]); }
