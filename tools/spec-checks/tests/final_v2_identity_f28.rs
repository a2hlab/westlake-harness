use std::path::Path;
use std::process::Command;

fn suite(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let directory = root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-identity-f28");
    let workspaces = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3")
        .arg(directory.join("test_successor.py")).arg(selector)
        .env("WORKSPACES", workspaces).env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root).status().expect("run offline f28 successor suite");
    assert!(status.success(), "f28 same-board full identity/driver gates failed");
}

#[test]
fn final_v2_identity_f28() { suite("IdentityTests"); }
#[test]
fn final_v2_driver_f28() { suite("DriverTests"); }
