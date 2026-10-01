use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-u11-native/test_window_shim.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run donor-derived U11 CPU window checks");
    assert!(status.success());
}

#[test]
fn u11_window_pixels() {
    check("PixelTests");
}

#[test]
fn u11_window_ownership() {
    check("OwnershipTests");
}

#[test]
fn u11_window_identity() {
    check("IdentityTests");
}
