use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u14-jar-image-plan/test_plan.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run offline U14 plan checks without private artifacts or builders");
    assert!(status.success());
}

#[test]
fn u14_jar_image_plan() {
    check("--plan");
}

#[test]
fn u14_native_slot_inputs() {
    check("--slots");
}
