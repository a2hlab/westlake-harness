use std::path::PathBuf;
use std::process::Command;
#[test]
fn u7_start_manifest_binding() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-commercial-game/u7-start-binding/test_binding.py"))
        .current_dir(root).output().expect("run offline real inherited U7 start regression");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
