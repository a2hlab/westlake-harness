use std::path::Path;
use std::process::Command;

// Verifies independent counterexample reproduction and evidence boundaries.
// This selector does not approve T36 safety, device behavior, or manual video.
#[test]
fn toutiao_host_reentry_peer() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .args(["-m", "unittest", "discover", "-s", "benchmark/2026-10-21-manual-video-regression/host-reentry-peer", "-p", "test_*.py"])
        .current_dir(root)
        .output()
        .expect("run independent offline replay");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
