use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_launch_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G17_SOURCE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| root.clone());
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-launch-observation-update/check_observation.py"))
        .arg("--source-root")
        .arg(source)
        .output()
        .expect("run offline launch observation checker");
    assert!(output.status.success(), "{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr));
}
