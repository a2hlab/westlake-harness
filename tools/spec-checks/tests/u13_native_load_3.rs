use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u13-native-load-3/test_analysis.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run read-only native loading adjudication checks");
    assert!(status.success());
}

#[test]
fn u13_native_load_3_evidence() {
    run_part("evidence");
}

#[test]
fn u13_native_load_3_predictions() {
    run_part("predictions");
}
