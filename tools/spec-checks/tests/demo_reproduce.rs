use std::path::Path;
use std::process::Command;
#[test]
fn demo_reproduce() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-demo-reproducibility/test_audit.py"))
        .output().expect("offline audit checks");
    assert!(result.status.success(), "{}", String::from_utf8_lossy(&result.stderr));
}
