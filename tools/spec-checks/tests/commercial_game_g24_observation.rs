use std::path::PathBuf;
use std::process::Command;

// G25: 60 observations with the 59-row prefix of master b2d14677a6 unchanged, renderer CSV/HTML/results
// consistent, every reference SHA verified, and negative cases (history drift, game success, candidate as
// current deployment, freeze, broken reference) refused. No device, REA or build.
#[test]
fn commercial_game_g24_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G25_SOURCE_ROOT").map(PathBuf::from).unwrap_or_else(|| root.clone());
    let output = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-21-g24-api-observation/check_observation.py"))
        .arg("--source-root").arg(source)
        .output().expect("run G25 observation checker");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
