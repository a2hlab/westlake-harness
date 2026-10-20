use std::{path::PathBuf, process::Command};
#[test]
fn ttvideo_t25_geometry() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t25-geometry/check.py"))
        .output().expect("run actual C host cases");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}

#[test]
fn ttvideo_t25_build_receipt() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .args(["-m", "unittest", "discover", "-s"])
        .arg(root.join("benchmark/2026-10-20-t25-geometry"))
        .args(["-p", "test_receipt.py", "-v"])
        .output().expect("verify actual build plus rejection fixtures");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
