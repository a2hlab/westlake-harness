use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-toutiao-bionic-scope/test_audit.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline Bionic audit tests");
    assert!(status.success());
}

#[test]
fn toutiao_bionic_identity() {
    check("IdentityTests");
}

#[test]
fn toutiao_bionic_consumers() {
    check("ConsumerTests");
}

#[test]
fn toutiao_bionic_candidate() {
    check("CandidateTests");
}

#[test]
fn toutiao_bionic_namespace() {
    check("NamespaceTests");
}
