use std::process::Command;
fn check(name: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("benchmark/2026-10-02-u12-assembly/test_assembly.py")
        .arg(name).current_dir(root).status().unwrap();
    assert!(status.success());
}
#[test] fn u12_assembly_native() { check("Tests.test_native"); }
#[test] fn u12_assembly_plans() { check("Tests.test_plans"); }
