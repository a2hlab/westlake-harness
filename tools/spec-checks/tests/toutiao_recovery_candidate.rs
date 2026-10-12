use std::path::Path;
use std::process::Command;

fn run(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-toutiao-recovery-candidate/tests/test_watchdog.py"))
        .arg(group)
        .current_dir(root)
        .status()
        .expect("execute real watchdog with isolated recording fixtures");
    assert!(status.success(), "Toutiao candidate {group} behavior failed");
}

#[test]
fn toutiao_recovery_candidate_consent() {
    run("ConsentTests");
}
#[test]
fn toutiao_recovery_candidate_data() {
    run("DataTests");
}
#[test]
fn toutiao_recovery_candidate_ownership() {
    run("OwnershipTests");
}
