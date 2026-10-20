use std::path::Path;
use std::process::Command;

#[test]
fn ttvideo_t30_production_prepare() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t30-request-recovery/production/check.py"))
        .current_dir(&root)
        .status().expect("T30 preparation checks");
    assert!(status.success(), "T30 preparation checks failed");
}
