use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_current_api_observations() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source = std::env::var_os("G15_SOURCE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|| root.clone());
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-current-api-observations/check_observations.py"))
        .arg("--source-root")
        .arg(source)
        .arg("--self-test")
        .output()
        .expect("run offline observation validator");
    assert!(output.status.success(), "{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr));
}
