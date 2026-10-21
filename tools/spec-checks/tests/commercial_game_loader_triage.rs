use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_loader_triage() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/runtime-loader-triage/check.py"))
        .current_dir(repo).status().expect("run pinned static evidence check");
    assert!(status.success(), "static evidence rejected; runtime remains unaccepted");
}

#[test]
fn commercial_game_loader_triage_g24_atfork() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/runtime-loader-triage/g24-atfork-addendum/check.py"))
        .current_dir(repo).status().expect("run G24 static addendum check");
    assert!(status.success(), "G24 source evidence rejected; provider winner remains unknown");
}
