use std::path::PathBuf;
use std::process::Command;
#[test]
fn ordinary_launch_increment_fixtures() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-24-ordinary-host-timeline/incremental-observer/test_observe.py"))
        .current_dir(root).status().expect("local synthetic fixtures only");
    assert!(status.success());
}
