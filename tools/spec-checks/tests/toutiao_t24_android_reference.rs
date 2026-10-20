use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t24_android_reference() {
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-20-t23-android-reference/check.py")).status().unwrap().success());
}
