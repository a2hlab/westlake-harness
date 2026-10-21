use std::{path::PathBuf, process::Command};
#[test]
fn demo61b_guardian_deployment() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-t34-demo61b-video/guardian-deployment-01/test_deploy.py"))
        .status().expect("run actual derived guardian transaction checks");
    assert!(status.success(), "guardian deployment offline checks failed");
}
