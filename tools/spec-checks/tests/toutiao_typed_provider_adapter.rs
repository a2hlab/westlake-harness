//! R15 offline typed provider only; no device calls or deployment artifacts.
use std::path::Path;
use std::process::Command;
fn check(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline/run_checks.py"))
        .arg(group).env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root)
        .status().expect("R15 actual offline build/oracle");
    assert!(result.success(), "R15 {group} failed");
}
#[test] fn ttvideo_typed_provider_pair() { check("pair"); }
#[test] fn ttvideo_typed_provider_layout() { check("layout"); }
#[test] fn ttvideo_typed_provider_failures() { check("failures"); }
#[test] fn ttvideo_typed_provider_concurrency() { check("concurrency"); }
#[test] fn ttvideo_typed_provider_receipt() { check("receipt"); }
