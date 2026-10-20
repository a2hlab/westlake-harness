use std::path::PathBuf;
use std::process::Command;

#[test]
fn ttvideo_t29_deployment_pending() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-20-t29-deployment/test_pending.py"))
        .current_dir(&repo)
        .output().expect("run actual Python pending checker tests");
    assert!(output.status.success(), "stdout={} stderr={}",
            String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}

#[test]
fn ttvideo_t29_deployment_final() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-20-t29-deployment/test_final.py"))
        .current_dir(&repo).output().expect("run actual final cross-link and drift checks");
    assert!(output.status.success(), "stdout={} stderr={}",
            String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
