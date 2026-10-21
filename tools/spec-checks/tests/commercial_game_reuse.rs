use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_reuse_receipt() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/reuse/check_receipt.py"))
        .current_dir(&repo).status().expect("start actual receipt checker");
    assert!(status.success(), "commercial game reuse evidence rejected; human acceptance remains pending");
}
