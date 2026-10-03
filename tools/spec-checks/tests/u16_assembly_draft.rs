use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u16-assembly-draft/test_draft.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run cold U16 disabled draft checks without private artifacts or builders");
    assert!(status.success());
}

#[test]
fn u16_draft_inputs() {
    check("--inputs");
}

#[test]
fn u16_draft_bake() {
    check("--bake");
}
