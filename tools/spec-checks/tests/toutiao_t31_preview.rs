use std::path::Path;
use std::process::Command;
fn run(name: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t31-demo-retain").join(name))
        .current_dir(&root).status().expect("T31 local-only check");
    assert!(status.success(), "T31 local-only check failed: {name}");
}
#[test]
fn ttvideo_t31_preview() { run("check_helpers.py"); }
#[test]
fn ttvideo_t31_recovery() { run("check_offline.py"); }
