use std::path::Path;
use std::process::Command;

#[test]
fn white_m3_glsurfaceview() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-white-m3-glsurfaceview/test_evidence.py"))
        .current_dir(root)
        .status()
        .expect("run M3 GL surface evidence checks");
    assert!(status.success());
}
