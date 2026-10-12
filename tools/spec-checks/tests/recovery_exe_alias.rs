use std::path::Path;
use std::process::Command;
fn check(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3").arg(root.join("benchmark/2026-10-12-recovery-exe-alias/test_alias.py"))
        .arg(group).current_dir(root).status().expect("offline exact-exe alias checks");
    assert!(status.success(), "exact-exe alias group failed");
}
#[test] fn recovery_exe_alias_identity() { check("IdentityTests"); }
#[test] fn recovery_exe_alias_reject() { check("RejectTests"); }
#[test] fn recovery_exe_alias_bindings() { check("BindingTests"); }
