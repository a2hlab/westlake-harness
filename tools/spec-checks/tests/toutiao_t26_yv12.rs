use std::{path::PathBuf, process::Command};
fn actual(suite: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t26-yv12/check.py"))
        .args(["--suite", suite]).output().expect("run pinned actual C tests");
    assert!(result.status.success(), "{}\n{}", String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr));
}
#[test] fn ttvideo_t26_layout() { actual("layout"); }
#[test] fn ttvideo_t26_bounds() { actual("bounds"); }
#[test] fn ttvideo_t26_failures() { actual("failures"); }
#[test] fn ttvideo_t26_route() { actual("route"); }
#[test] fn ttvideo_t26_ownership() { actual("ownership"); }
#[test] fn ttvideo_t26_regression() { actual("regression"); }
#[test] fn ttvideo_t26_receipt() { actual("receipt"); }
