use std::path::Path;
use std::process::Command;

fn run(group: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-toutiao-recovery-integration/tests/test_integration.py"))
        .arg(group)
        .current_dir(root)
        .status()
        .expect("run only offline integration tests");
    assert!(status.success(), "integration {group} failed");
}

#[test]
fn toutiao_recovery_integration_bindings() { run("BindingsTests"); }
#[test]
fn toutiao_recovery_integration_preview() { run("PreviewTests"); }
#[test]
fn toutiao_recovery_integration_launch() { run("LaunchTests"); }
