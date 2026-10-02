use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u13-compat-ctype/test_analysis.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run landed-source ctype checks without private artifacts");
    assert!(status.success());
}

#[test]
fn u13_compat_ctype_native() {
    run_part("native");
}

#[test]
fn u13_compat_ctype_draft() {
    run_part("draft");
}
