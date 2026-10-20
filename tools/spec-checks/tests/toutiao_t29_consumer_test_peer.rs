use std::path::PathBuf;
use std::process::Command;
#[test]
fn ttvideo_t29_consumer_peer() {
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result=Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t29-consumer-test-peer/test_runner.py"))
        .current_dir(&root).output().expect("real consumer fixture tests");
    assert!(result.status.success(),"{}",String::from_utf8_lossy(&result.stderr));
}
