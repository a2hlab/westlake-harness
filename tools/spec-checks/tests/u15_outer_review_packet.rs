use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-outer-review-packet/test_packet.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run cold U15 outer review checks");
    assert!(status.success());
}

#[test]
fn u15_outer_classes() {
    check("--classes");
}

#[test]
fn u15_outer_registry() {
    check("--registry");
}
