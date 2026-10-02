use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u13-assembly-draft/test_analysis.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run offline disabled U13 draft checks");
    assert!(status.success());
}

#[test]
fn u13_assembly_draft_disabled() {
    run_part("disabled");
}

#[test]
fn u13_assembly_draft_evidence() {
    run_part("evidence");
}
