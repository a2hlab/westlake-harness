use std::path::PathBuf;
use std::process::Command;

#[test]
fn commercial_game_extractor_build_receipt() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent().unwrap().parent().unwrap().to_path_buf();
    let mut cmd = Command::new("python3");
    cmd.arg(repo.join("benchmark/2026-10-21-commercial-game/apk-extractor/native-build/check_receipt.py"));
    if let Some(path) = std::env::var_os("G09_BUILD_RUN") { cmd.arg("--build-run").arg(path); }
    let status = cmd.current_dir(&repo).status().expect("run G09 actual receipt checker");
    assert!(status.success(), "G09 receipt rejected; without G09_BUILD_RUN this checks public actual-build receipts only");
}
