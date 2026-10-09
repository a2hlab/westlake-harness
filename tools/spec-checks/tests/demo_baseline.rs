use std::path::Path;
use std::process::Command;

#[test]
fn demo_baseline_board_choice() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-09-demo-baseline/test_board_choice.py"))
        .arg("-v")
        .current_dir(root)
        .status()
        .expect("run recorded three-board read-only known answers");
    assert!(status.success());
}

// A scoped helper test. Do not use demo_baseline_seal: restore and runbook are pending.
#[test]
fn demo_baseline_selfcheck() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-09-demo-baseline/selfcheck/test_selfcheck.py"))
        .arg("-v")
        .current_dir(root)
        .status()
        .expect("run read-only demo selfcheck known answers without a device");
    assert!(status.success());
}
