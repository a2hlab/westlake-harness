use std::path::Path;
use std::process::Command;

#[test]
fn u14_stage_b_selector_fix() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-08-u14-stage-b-selector-fix/test_selector.py"))
        .current_dir(root)
        .status()
        .expect("run U14 candidate union known answers");
    assert!(status.success());
}
