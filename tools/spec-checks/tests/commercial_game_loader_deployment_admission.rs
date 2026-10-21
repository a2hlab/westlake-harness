use std::path::Path;
use std::process::Command;

// Offline evidence integrity and negative admission cases; never deploys.
#[test]
fn commercial_game_loader_deployment_admission() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg("benchmark/2026-10-21-commercial-game/loader-deployment-admission/check.py")
        .current_dir(root)
        .output()
        .expect("run persistent G19 offline checker");
    println!("{}", String::from_utf8_lossy(&output.stdout));
    assert!(
        output.status.success(),
        "{}\n{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
}
