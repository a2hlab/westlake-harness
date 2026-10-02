use std::path::Path;
use std::process::Command;

#[test]
fn bms_source_reconcile() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-bms-source-reconcile/test_audit.py"))
        .current_dir(root)
        .status()
        .expect("run deployed source reconciliation checks");
    assert!(status.success());
}
