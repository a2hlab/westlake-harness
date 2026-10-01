use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-webview-startup-prediction/test_webview.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline WebView startup checks");
    assert!(status.success());
}

#[test]
fn webview_startup_identity() {
    check("IdentityTests");
}

#[test]
fn webview_startup_scope() {
    check("ScopeTests");
}

#[test]
fn webview_startup_replay() {
    check("ReplayTests");
}
