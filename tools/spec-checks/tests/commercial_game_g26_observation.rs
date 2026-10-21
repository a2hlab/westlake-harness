use std::path::PathBuf;
use std::process::Command;

// G29: exactly 61 observations with master 83d1a6e07's 60-row prefix unchanged, original-renderer byte
// equality, every reference SHA verified, and negative cases (history drift, HTML-only success, truncation,
// 62nd row, dropped evidence, freeze/deployment/playable/clean-rebuild claims) refused. No device/REA/build.
#[test]
fn commercial_game_g26_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G29_SOURCE_ROOT").map(PathBuf::from).unwrap_or_else(|| root.clone());
    let output = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-21-g26-api-observation/check_observation.py"))
        .arg("--source-root").arg(source)
        .output().expect("run G29 observation checker");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
