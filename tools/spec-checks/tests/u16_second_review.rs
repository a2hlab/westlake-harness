use std::path::Path;
use std::process::Command;

#[test]
fn u16_second_review_evidence() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u16-second-review/test_packet.py"))
        .current_dir(root)
        .status()
        .expect("run offline U16 second approval packet tests");
    assert!(status.success());
}
