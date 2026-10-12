use std::process::Command;
fn run(class: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-seal-snapshot-adapter/test_adapter.py"))
        .args([class, "-v"]).output().expect("offline snapshot checks");
    assert!(out.status.success(), "{}{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
#[test]
fn seal_snapshot_adapter_identity() { run("Identity"); }
#[test]
fn seal_snapshot_adapter_completeness() { run("Completeness"); }
