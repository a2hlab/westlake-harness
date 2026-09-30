use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u7-prospective/test_skeleton.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline U7 skeleton tests");
    assert!(status.success());
}

#[test]
fn u7_draft_coverage() {
    run("CoverageTests");
}

#[test]
fn u7_repair_catalog() {
    run("CatalogTests");
}

#[test]
fn u7_pending_intake() {
    run("IntakeTests");
}

#[test]
fn u7_scoring_separation() {
    run("ScoringTests");
}
