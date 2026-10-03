use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u14-on-u13-base/test_binding.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run U14 on U13 cold binding checks");
    assert!(status.success());
}

#[test]
fn u14_u13_binding() {
    check("--binding");
}

#[test]
fn u14_u13_replay() {
    check("--replay");
}
