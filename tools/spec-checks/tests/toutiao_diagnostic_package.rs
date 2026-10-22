use std::path::Path;
use std::process::Command;

#[test]
fn toutiao_diagnostic_package() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .arg("benchmark/2026-10-22-toutiao-diagnostic-package/check.py")
        .current_dir(root)
        .output()
        .expect("run local T47 package checks");
    assert!(result.status.success(), "{}\n{}",
        String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr));
}
