use std::path::Path;
use std::process::Command;

#[test]
fn u12_ppsspp_dlext() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-ppsspp-dlext/test_boundary.py"))
        .current_dir(root)
        .status()
        .expect("run PPSSPP backend boundary checks");
    assert!(status.success());
}
