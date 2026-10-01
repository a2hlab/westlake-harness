use std::path::PathBuf;
use std::process::Command;

fn run(file: &str, class: Option<&str>) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut cmd = Command::new("python3");
    cmd.arg(root.join("benchmark/2026-10-01-n10-native").join(file));
    if let Some(name) = class { cmd.arg(name); }
    assert!(cmd.current_dir(root).status().unwrap().success());
}

#[test] fn n10_identity() { run("verify.py", Some("IdentityTests")); }
#[test] fn n10_package() { run("verify.py", Some("PackageTests")); }
#[test] fn n10_recovery() { run("test_recovery.py", None); }
#[test] fn n10_gates() { run("verify.py", Some("GateTests")); }
