use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-n11h-host-owner/test_candidate.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline N11h host tests");
    assert!(status.success());
}

#[test]
fn n11h_baseline() {
    check("BaselineTests");
}

#[test]
fn n11h_namespace() {
    check("NamespaceTests");
}

#[test]
fn n11h_open() {
    check("OpenTests");
}

#[test]
fn n11h_artifact() {
    check("ArtifactTests");
}
