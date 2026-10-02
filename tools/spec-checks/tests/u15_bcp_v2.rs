use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u15-bcp-v2/test_plan.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run cold U15 double-BCP plan checks without builders or private artifacts");
    assert!(status.success());
}

#[test]
fn u15_bcp_v2_inputs() {
    check("--inputs");
}

#[test]
fn u15_bcp_v2_recipe() {
    check("--recipe");
}
