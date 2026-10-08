use std::path::Path;
use std::process::Command;

#[test]
fn lit_apps_report_inventory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-08-lit-apps-report/test_report.py"))
        .current_dir(root)
        .status()
        .expect("run lit application inventory known answers");
    assert!(status.success());
}
