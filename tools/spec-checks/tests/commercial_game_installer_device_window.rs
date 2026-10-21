use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_installer_device_window() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3").arg(repo.join("benchmark/2026-10-21-commercial-game/apk-extractor/device-window/check_offline.py"))
        .current_dir(repo).status().expect("offline G13 rejection cases");
    assert!(status.success());
}
