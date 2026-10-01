use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan-tests/test_fixplan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U8 fixplan evidence checks");
    assert!(status.success());
}

#[test]
fn u8_fixplan_report() {
    check("ReportTests");
}

#[test]
fn u8_fixplan_sources() {
    check("SourceTests");
}

#[test]
fn u8_fixplan_uncertainty() {
    check("UncertaintyTests");
}
