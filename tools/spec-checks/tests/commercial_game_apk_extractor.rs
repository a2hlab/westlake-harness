use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_apk_extractor_receipt() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/apk-extractor/check_receipt.py"))
        .current_dir(&repo).status().expect("run exact source/replay receipt check");
    assert!(status.success(), "G08 source or actual replay evidence mismatch");
}
