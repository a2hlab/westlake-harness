use std::path::Path;
use std::process::Command;

fn check(folder: &str, script: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark").join(folder).join(script))
        .current_dir(root)
        .status()
        .expect("run offline native cluster checks");
    assert!(status.success());
}

#[test]
fn u12_libresudoku_icu() {
    check("2026-10-02-u12-libresudoku-icu", "test_coverage.py");
}
