use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_native_route_candidate() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/native-route-candidate/check_delivery.py"))
        .arg("--routes").current_dir(repo).status().expect("run exact G26 source/receipt and production C boundary checks");
    assert!(status.success(), "offline evidence failed; this selector never authorizes device execution");
}
