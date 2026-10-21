use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_native_route_package() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-commercial-game/native-route-package/check_receipt.py"))
        .output().expect("check unsigned G27 inputs without device or build");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
