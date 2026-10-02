use std::path::Path;
use std::process::Command;

#[test]
fn white_m2_webview() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-white-m2-webview/test_evidence.py"))
        .current_dir(root)
        .status()
        .expect("run M2 WebView evidence checks");
    assert!(status.success());
}
