use std::path::Path;
use std::process::Command;

#[test]
fn spare_installer_offline() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-10-spare-installer-unify/test_installer.py"))
        .arg("-v")
        .current_dir(root)
        .status()
        .expect("run offline installer transaction known answers");
    assert!(status.success());
    println!("OFFLINE_ONLY: no board access; time window and actual reboot UI acceptance pending");
}
