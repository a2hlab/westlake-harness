use std::process::Command;
fn run(test: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3").arg("benchmark/2026-10-01-n11b-early-owner/verify.py")
        .arg(test).current_dir(root).status().unwrap();
    assert!(status.success());
}
#[test] fn n11b_identity() { run("Tests.test_identity"); }
#[test] fn n11b_owner() { run("Tests.test_owner"); }
#[test] fn n11b_package() { run("Tests.test_package"); }
