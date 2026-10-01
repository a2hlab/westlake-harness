use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-last-session-scan/test_scan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run last-session evidence scan tests");
    assert!(status.success());
}

#[test]
fn last_session_parser() {
    check("ParserTests");
}

#[test]
fn last_session_impact() {
    check("ImpactTests");
}

#[test]
fn last_session_cohort() {
    check("CohortTests");
}
