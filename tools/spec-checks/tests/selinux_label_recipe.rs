use std::path::Path;
use std::process::Command;

#[test]
fn selinux_label_recipe() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("scripts/lab/test_selinux_label_audit.py"))
        .arg("-v")
        .current_dir(root)
        .status()
        .expect("run read-only SELinux recipe and guarded start fixtures");
    assert!(status.success());
    println!("OFFLINE_ONLY: mocked transport; no security policy or device changes");
}
