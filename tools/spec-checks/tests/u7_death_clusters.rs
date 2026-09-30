use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u7-death-clusters/test_clusters.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U7 unlit-cluster evidence tests");
    assert!(status.success());
}

#[test]
fn u7_death_evidence() {
    check("EvidenceTests");
}

#[test]
fn u7_death_threads() {
    check("ThreadTests");
}

#[test]
fn u7_death_clusters() {
    check("ClusterTests");
}
