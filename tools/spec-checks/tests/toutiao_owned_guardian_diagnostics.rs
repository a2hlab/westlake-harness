use std::path::Path;
use std::process::Command;

#[test]
fn toutiao_owned_guardian_diagnostics() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg("benchmark/2026-10-22-toutiao-owned-guardian-diagnostics/check.py")
        .current_dir(root)
        .output()
        .expect("run T46 synthetic guardian branch replay");
    assert!(output.status.success(), "{}\n{}",
        String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
