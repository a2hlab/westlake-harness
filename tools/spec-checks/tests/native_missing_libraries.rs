use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-native-missing-libraries/test_handoff.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline missing library handoff checks");
    assert!(status.success());
}

#[test]
fn native_missing_library_evidence() { check("EvidenceTests"); }

#[test]
fn native_missing_library_handoff() { check("HandoffTests"); }

#[test]
fn native_missing_library_policy() { check("PolicyTests"); }
