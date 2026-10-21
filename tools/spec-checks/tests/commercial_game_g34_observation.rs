use std::path::PathBuf;
use std::process::Command;

// G35: exactly 64 observations with master 86b9fdb160's 63-row prefix unchanged, original-renderer byte
// equality, references equal to the G34 landing-derived set with every SHA verified, G34 receipt
// cross-checks, and negative cases (history drift, truncation to 63, 65th row, missing reference, SHA
// drift, HTML/CSV-only false success, current deployment, freeze, game frame, known root cause, Dfx
// CODE-31 or rc0 force-stop as success, historical pending rewritten) refused. No device/REA/build.
#[test]
fn commercial_game_g34_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G35_SOURCE_ROOT").map(PathBuf::from).unwrap_or_else(|| root.clone());
    let output = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-21-g34-api-observation/check_observation.py"))
        .arg("--source-root").arg(source)
        .output().expect("run G35 observation checker");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
