use std::path::Path;
use std::process::Command;

fn run(command: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-api-progress/atlas.py"))
        .arg(command)
        .current_dir(root)
        .status()
        .expect("run real API evidence validation");
    assert!(status.success(), "API atlas {command} validation failed");
}

#[test]
fn api_progress_registry() {
    run("registry");
}
#[test]
fn api_progress_java() {
    run("java");
}
#[test]
fn api_progress_native() {
    run("native");
}
#[test]
fn api_progress_atlas() {
    run("check");
    run("negative");
}
