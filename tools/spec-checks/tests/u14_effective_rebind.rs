use std::path::Path;
use std::process::Command;

fn run_checks(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u14-effective-rebind/test_binding.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run conditional U14 checks from public evidence only");
    assert!(status.success());
}

#[test]
fn u14_effective_binding() {
    run_checks("binding");
}

#[test]
fn u14_effective_preview() {
    run_checks("preview");
}
