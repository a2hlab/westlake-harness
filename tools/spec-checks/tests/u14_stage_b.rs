use std::path::Path;
use std::process::Command;

fn check(mode: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-u14-stage-b/test_promotion_u14.py"))
        .arg(mode)
        .current_dir(root)
        .status()
        .expect("run disabled U14 promotion checks");
    assert!(status.success());
}

#[test]
fn u14_promotion_binding() {
    check("--binding");
}

#[test]
fn u14_promotion_known_answers() {
    check("--known-answers");
}
