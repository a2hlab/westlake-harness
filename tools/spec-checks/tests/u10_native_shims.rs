use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u10-native-shims/test_shims.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U10 compat shim checks");
    assert!(status.success());
}

#[test]
fn u10_shim_evidence() {
    check("EvidenceTests");
}

#[test]
fn u10_shim_behavior() {
    check("BehaviorTests");
}

#[test]
fn u10_shim_loader() {
    check("LoaderTests");
}

fn check_visibility(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u10-native-shims/test_visibility_policy.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U10 policy and resident-owner checks");
    assert!(status.success());
}

#[test]
fn u10_policy_additive() {
    check_visibility("PolicyTests");
}

#[test]
fn u10_abort_visibility() {
    check_visibility("VisibilityTests");
}

#[test]
fn u10_opensles_abi_evidence() {
    check_visibility("OpenSLESEvidenceTests");
}
