use std::path::PathBuf;
use std::process::Command;
fn run(names: &[&str]) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize().unwrap();
    let mut cmd = Command::new("python3");
    cmd.arg("test_restore.py");
    for name in names { cmd.arg(format!("RestoreTests.{}", name)); }
    let output = cmd.current_dir(root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/routeb-fresh-restore"))
        .env("WORKSPACES", root.parent().unwrap()).env("PYTHONDONTWRITEBYTECODE", "1")
        .output().expect("offline current487 tests");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
#[test]
fn routeb_fresh_compile() { run(&["test_compile_actual_and_cli_preview"]); }
#[test]
fn routeb_fresh_reject() { run(&["test_authorization_scope_and_rollback_reserve", "test_foreign_before_zero_send_and_inode_guard", "test_real_shell_protocol_rejects_host_rc_only"]); }
#[test]
fn routeb_fresh_transaction() { run(&["test_partial_stage_rollback_and_unknown_audit_reject"]); }
#[test]
fn routeb_fresh_receipt() { run(&["test_full487_real_cli_recording_and_missing_receipt"]); }
