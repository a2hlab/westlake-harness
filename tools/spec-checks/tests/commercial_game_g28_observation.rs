use std::path::PathBuf;
use std::process::Command;

// G31: exactly 62 observations with master 782b588de8's 61-row prefix unchanged, original-renderer byte
// equality, every reference SHA verified, G28 receipt cross-checks, and negative cases (history drift, false
// success, HTML-only fake frame, truncation to 61, 63rd row, dropped evidence, missing reference, SHA drift,
// atfork/maps/held-receipt/private-check claims) refused. No device/REA/build.
#[test]
fn commercial_game_g28_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G31_SOURCE_ROOT").map(PathBuf::from).unwrap_or_else(|| root.clone());
    let output = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-21-g28-api-observation/check_observation.py"))
        .arg("--source-root").arg(source)
        .output().expect("run G31 observation checker");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
