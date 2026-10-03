use std::path::Path;
use std::process::Command;

#[test]
fn u15_u16_gate_batch_guards() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-u16-gate-batch/test_batch.py"))
        .current_dir(root)
        .status()
        .expect("run guarded U15/U16 gate batch known answers");
    assert!(status.success());
}
