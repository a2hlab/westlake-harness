use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u8-death-clusters/no-fatal-tests/test_terminations.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U8 termination replay checks");
    assert!(status.success());
}

#[test]
fn u8_termination_matching() { check("MatchingTests"); }

#[test]
fn u8_termination_report() { check("ReportTests"); }
