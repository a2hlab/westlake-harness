use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_locale_abi_candidate() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().to_path_buf();
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-21-commercial-game/locale-abi-candidate/check_delivery.py"))
        .arg("--host").current_dir(repo).status().expect("run public evidence and real locale/native body regressions");
    assert!(status.success(), "G30 offline checks failed; no device authorization");
}
