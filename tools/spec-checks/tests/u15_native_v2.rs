use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-native-v2/test_draft.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run cold U15 native v2 snapshot checks");
    assert!(status.success());
}

#[test]
fn u15_native_v2_composition() {
    check("--composition");
}

#[test]
fn u15_native_v2_review() {
    check("--review");
}
