use std::path::Path;
use std::process::Command;

#[test]
fn u13_final_assembly() {
    run_checks();
}

#[test]
fn u13_final_production() {
    run_checks();
}

fn run_checks() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u13-final-assembly/test_final.py"))
        .current_dir(root)
        .status()
        .expect("run disabled U13 final assembly checks");
    assert!(status.success());
}
