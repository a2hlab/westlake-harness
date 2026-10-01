use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-b10-theme-graphics/test_impact.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run B10 theme and graphics impact checks");
    assert!(status.success());
}

#[test]
fn b10_theme_graphics_identity() {
    check("IdentityTests");
}

#[test]
fn b10_theme_graphics_actionbar() {
    check("ActionbarTests");
}

#[test]
fn b10_theme_graphics_native() {
    check("NativeTests");
}

#[test]
fn b10_theme_graphics_replay() {
    check("ReplayTests");
}
