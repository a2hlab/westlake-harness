use std::path::Path;
use std::process::Command;

#[test]
fn u13_effective_rebind() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u13-effective-rebind/test_rebind.py"))
        .current_dir(root)
        .status()
        .expect("run effective U10.1T8 binding checks");
    assert!(status.success());
}
