use std::path::Path;
use std::process::Command;

#[test]
fn verified_source_publication() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status = Command::new("python3")
        .arg("-m").arg("unittest").arg("test_closeout")
        .current_dir(root.join("benchmark/2026-10-14-api-source-delivery"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("source publication amendment guard");
    assert!(status.success(), "Source-only amendments must preserve original API grades and reject untracked source");
}
