use std::path::Path;
use std::process::Command;

#[test]
fn host_window_record_reader_fixtures() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-24-native-host-window-recovery/record-reader/run_tests.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .expect("execute actual production C++ reader build and fixtures");
    println!("{}", String::from_utf8_lossy(&result.stdout));
    eprintln!("{}", String::from_utf8_lossy(&result.stderr));
    assert!(result.status.success(), "production reader tests failed");
}
