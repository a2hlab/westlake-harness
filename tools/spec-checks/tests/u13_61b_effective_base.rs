use std::path::Path;
use std::process::Command;

#[test]
fn u13_61b_effective_base() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u13-61b-effective-base/test_base.py"))
        .current_dir(root)
        .status()
        .expect("run board-local metadata checks without private artifacts");
    assert!(status.success());
}
