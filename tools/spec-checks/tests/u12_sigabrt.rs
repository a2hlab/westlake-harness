use std::path::Path;
use std::process::Command;

#[test]
fn u12_sigabrt_evidence() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-sigabrt/test_analysis.py"))
        .current_dir(root)
        .status()
        .expect("run read-only SIGABRT evidence checks");
    assert!(status.success());
}
