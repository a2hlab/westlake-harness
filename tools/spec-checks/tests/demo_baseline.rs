use std::path::{Path, PathBuf};
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

#[test]
fn demo_baseline_sepolicy_gate() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let base = root.clone();
    let script = base.join("scripts/lab/test_sepolicy_gate.py");
    if !script.is_file() {
        panic!("sepolicy gate tests not found at {}", script.display());
    }
    let status = Command::new("python3")
        .arg(script)
        .arg("-v")
        .current_dir(&base)
        .status()
        .expect("run offline sepolicy gate known answers (sesearch in a2hlab)");
    assert!(status.success());
}
