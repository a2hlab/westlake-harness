use std::path::PathBuf;
use std::process::Command;
fn run(file: &str, class: Option<&str>) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut cmd = Command::new("python3");
    cmd.arg(root.join("benchmark/2026-10-01-u7-executor").join(file));
    if let Some(name) = class { cmd.arg(name); }
    assert!(cmd.current_dir(root).status().unwrap().success());
}
#[test] fn u7_transaction() { run("test_executor.py", Some("TransactionTests")); }
#[test] fn u7_recovery() { run("test_executor.py", Some("RecoveryTests")); }
#[test] fn u7_preflight() { run("test_executor.py", Some("PreflightTests")); }
#[test] fn u7_format() { run("test_format.py", None); }
#[test] fn u7_approved_provenance() { run("test_executor.py", Some("ProvenanceTests")); }
#[test] fn u7_baseline_replay() { run("test_executor.py", Some("BaselineReplayTests")); }
#[test] fn u7_board_evidence() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    assert!(Command::new("python3").arg(root.join("benchmark/2026-10-01-u7-executor/board61b/check_evidence.py")).status().unwrap().success());
}
