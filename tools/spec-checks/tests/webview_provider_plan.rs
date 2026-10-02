use std::path::Path;
use std::process::Command;

fn run_part(part: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-webview-provider-plan/test_plan.py"))
        .args(["--part", part])
        .current_dir(root)
        .status()
        .expect("run offline WebView plan checks");
    assert!(status.success());
}

#[test]
fn webview_provider_plan_evidence() {
    run_part("evidence");
}

#[test]
fn webview_provider_plan_phases() {
    run_part("phases");
}
