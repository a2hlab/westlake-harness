use std::path::Path;
use std::process::Command;

// G11: every crosswalk reference re-hashes against the main repository, recorded statuses never upgrade
// the verification scope (Genshin not started, Toutiao white-screen fix pending), and gaps stay explicit.
#[test]
fn dual_track_source_api_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let script = root.join("benchmark/2026-10-21-dual-track-source-api/check_crosswalk.py");
    let mut cmd = Command::new("python3");
    cmd.arg("-B").arg("-I").arg(&script);
    if let Ok(main) = std::env::var("WESTLAKE_MAIN") { cmd.arg("--source-root").arg(main); }
    assert!(cmd.status().expect("python3").success(), "G11 crosswalk check failed");
}
