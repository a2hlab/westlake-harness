use std::path::Path;
use std::process::Command;

#[test]
fn demo_baseline_adapter_buildchain() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-10-adapter-buildchain/test_rebuild_gate.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run actual identities and fail-closed rebuildability known answers");
    assert!(status.success());
    let cold = Command::new("python3")
        .arg(root.join("benchmark/2026-10-10-adapter-buildchain/test_runtime_cold.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run independent cold-directory preparation known answers");
    assert!(cold.success());
    // The contract includes two real clean adapter reproductions. Fixture-only
    // guard tests cannot certify that scenario; require the actual receipt gate.
    let actual = Command::new("python3")
        .arg(root.join("benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py"))
        .arg("--require-reproduced")
        .current_dir(&root)
        .status()
        .expect("read actual target clean-build receipts");
    assert!(actual.success(), "REAL_REPRODUCTION_BLOCKED: support tests are not adapter846/8ab receipts");
}

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

#[test]
fn demo_baseline_manifest() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-09-demo-baseline/test_manifest.py"))
        .current_dir(root)
        .status()
        .expect("run demo inventory identity and coverage checks");
    assert!(status.success());
}

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

#[test]
fn demo_baseline_seal() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for selector in ["test_seal.py", "test_delivery.py"] {
        let status = Command::new("python3")
            .args(["-m", "unittest", "discover", "-s"])
            .arg(root.join("benchmark/2026-10-09-demo-baseline/t5"))
            .args(["-p", selector, "-v"])
            .current_dir(&root)
            .status()
            .expect("run seal/runbook/offline restoration known answers");
        assert!(status.success());
    }
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-09-demo-baseline/selfcheck/test_selfcheck.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run actual selfcheck CLI drift fixtures");
    assert!(status.success());
    println!("OFFLINE_ONLY: live spare-board rehearsal and final seal remain pending");
}
