use std::path::PathBuf;
use std::process::Command;

// G33: exactly 63 observations with master e4cd7d753's 62-row prefix unchanged, original-renderer byte
// equality, references equal to the 56 fixed G30 public paths with every SHA verified, G30 receipt
// cross-checks, and negative cases (history drift, false success, HTML-only success, truncation to 62,
// 64th row, dropped evidence, missing reference, SHA drift, freeze/deployment/playable/remote-archive/
// OS-closure/rc124/__assert2 claims) refused. No device/REA/build.
#[test]
fn commercial_game_g30_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G33_SOURCE_ROOT").map(PathBuf::from).unwrap_or_else(|| root.clone());
    let output = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-21-g30-api-observation/check_observation.py"))
        .arg("--source-root").arg(source)
        .output().expect("run G33 observation checker");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
