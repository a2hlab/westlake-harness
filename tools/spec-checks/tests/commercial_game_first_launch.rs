use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_first_launch_receipt() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-commercial-game/first-launch/check_receipt.py"))
        .current_dir(&root).status().expect("run real G06 offline receipt and recovery checks");
    assert!(status.success(), "G06 offline failure; device scenarios are still pending human review");
}
