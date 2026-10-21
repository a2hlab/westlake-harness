use std::path::PathBuf;
use std::process::Command;
#[test]
fn commercial_game_gles_transaction_package() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-commercial-game/gles-transaction-package/check_receipt.py"))
        .output().expect("check unsigned G20 package evidence offline");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
