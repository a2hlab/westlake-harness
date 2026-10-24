use std::path::Path;
use std::process::Command;

#[test]
fn host_window_session_recovery_fixtures() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-24-native-host-window-recovery/session-recovery/run_tests.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output()
        .expect("compile production recovery coordinator, routing, and accepted t1 reader");
    println!("{}", String::from_utf8_lossy(&output.stdout));
    eprintln!("{}", String::from_utf8_lossy(&output.stderr));
    assert!(output.status.success(), "native recovery fixtures failed");
}
