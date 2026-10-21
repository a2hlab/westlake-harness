use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_environment_readiness() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/apk-extractor/environment-readiness/check_receipt.py"))
        .current_dir(&repo).status().expect("validate recorded G10 evidence without remote operations");
    assert!(status.success(), "G10 receipt inconsistent");
}
