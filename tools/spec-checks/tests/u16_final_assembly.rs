use std::path::Path;
use std::process::Command;

#[test]
fn u16_final_assembly_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u16-final-assembly/test_receipt.py"))
        .current_dir(root)
        .status()
        .expect("run offline U16 receipt invariants");
    assert!(status.success());
}
