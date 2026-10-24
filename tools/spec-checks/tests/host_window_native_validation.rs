use std::path::Path;
use std::process::Command;

#[test]
fn host_window_native_validation_receipts() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-24-native-host-window-recovery/device-validation/test_receipts.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .expect("run pure offline synthetic receipt checker tests");
    println!("{}", String::from_utf8_lossy(&output.stdout));
    eprintln!("{}", String::from_utf8_lossy(&output.stderr));
    assert!(output.status.success(), "offline receipt checker tests failed; no device verdict implied");
}
