use std::path::Path;
use std::process::Command;
#[test]
fn demo_desktop_inventory() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-demo-desktop-inventory/inventory.py"))
        .arg("check").env("WORKSPACES", ws).env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root).status().expect("offline inventory provenance and action safety checks");
    assert!(status.success(), "Inventory data check failed; current device/UI checks remain pending");
}
