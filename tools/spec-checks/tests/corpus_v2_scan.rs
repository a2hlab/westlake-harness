use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-corpus-v2/apk-scan-v1/test_scan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run corpus-v2 APK checks");
    assert!(status.success());
}

#[test]
fn corpus_v2_scan_identity() {
    check("IdentityTests");
}

#[test]
fn corpus_v2_scan_rules() {
    check("RuleTests");
}

#[test]
fn corpus_v2_scan_freeze() {
    check("FreezeTests");
}

#[test]
fn corpus_v2_scan_replay() {
    check("ReplayTests");
}
