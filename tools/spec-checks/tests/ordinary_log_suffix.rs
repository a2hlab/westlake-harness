use std::path::Path;
use std::process::Command;
#[test]
fn ordinary_log_suffix_identity() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-24-ordinary-log-suffix/test_identity.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("run offline identity tests");
    assert!(status.success(), "identity refusal tests failed");
}
