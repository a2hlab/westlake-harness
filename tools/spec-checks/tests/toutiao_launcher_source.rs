use std::{env, path::PathBuf, process::Command};
#[test]
fn t31_launcher_source_review() {
    let repo = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let main = env::var_os("LAUNCHER_MAIN").map(PathBuf::from).unwrap_or_else(|| repo.join("../westlake-harness"));
    let vm = env::var_os("LAUNCHER_VM_COPY").map(PathBuf::from).unwrap_or_else(|| repo.join("../vm-copies/westlake-current"));
    let status = Command::new("python3")
        .arg(repo.join("benchmark/2026-10-20-t31-launcher-triage/check_evidence.py"))
        .arg("--main").arg(main).arg("--vm-copy").arg(vm).status().expect("python3");
    assert!(status.success(), "source/provenance mismatch; not a device test");
}
