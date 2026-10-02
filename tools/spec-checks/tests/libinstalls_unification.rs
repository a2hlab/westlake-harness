use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-libinstalls-unification/test_audit.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline installation-service audit");
    assert!(status.success());
}

#[test]
fn libinstalls_identity() {
    check("IdentityTests");
}

#[test]
fn libinstalls_payload_policy() {
    check("PolicyTests");
}

#[test]
fn libinstalls_install_stats() {
    check("StatsTests");
}

#[test]
fn libinstalls_alignment_plan() {
    check("PlanTests");
}
