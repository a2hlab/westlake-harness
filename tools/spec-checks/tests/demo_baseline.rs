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
    // t2c outcome (14:30 deadline, user 2026-10-10): the runtime is reproduced by two logged
    // clean builds; both adapters are locked parts. Assert exactly that, so a later reproduction
    // or a lost runtime receipt both show up here instead of a permanently red selector.
    let gate = |artifact: &str| {
        Command::new("python3")
            .arg(root.join("benchmark/2026-10-10-adapter-buildchain/rebuild_gate.py"))
            .args(["--artifact", artifact, "--require-reproduced"])
            .current_dir(&root)
            .status()
            .expect("read clean-build receipts")
            .code()
    };
    assert_eq!(gate("runtime-u13-18763dd4"), Some(0), "runtime 18763dd4 must stay reproduced");
    for adapter in ["adapter-u13-84695d62", "adapter-boat-8ab85446"] {
        assert_eq!(gate(adapter), Some(2), "{adapter} is a locked part: the gate must still refuse it");
    }
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
