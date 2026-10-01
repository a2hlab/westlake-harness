use std::process::Command;
fn check(name: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3").arg("benchmark/2026-10-01-u9-native/verify.py").arg(name).current_dir(root).status().unwrap();
    assert!(status.success());
}
#[test] fn u9_native_inputs() { check("Tests.test_inputs"); }
#[test] fn u9_native_build() { check("Tests.test_build"); }
#[test] fn u9_native_package() { check("Tests.test_package"); }
