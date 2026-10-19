//! Offline injected-ops module only. No device, shared library, or production route.
use std::path::Path;
use std::process::Command;
fn check(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/run_checks.py"))
        .arg(group).env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root)
        .status().expect("R14 offline host checks");
    assert!(status.success(), "R14 {group} failed");
}
#[test] fn ttvideo_window_offline_pair() { check("pair"); }
#[test] fn ttvideo_window_offline_failures() { check("failures"); }
#[test] fn ttvideo_window_offline_concurrency() { check("concurrency"); }
#[test] fn ttvideo_window_offline_receipt() { check("receipt"); }
