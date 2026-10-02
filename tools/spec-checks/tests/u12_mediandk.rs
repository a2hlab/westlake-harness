use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-mediandk/test_analysis.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run admitted source and pinned media evidence tests");
    assert!(status.success());
}

#[test]
fn u12_mediandk_evidence() {
    run("EvidenceTests");
}

#[test]
fn u12_mediandk_provider() {
    run("ProviderTests");
}
