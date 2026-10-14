use std::path::Path;
use std::process::Command;

#[test]
fn api_source_delivery() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES")
        .unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-api-source-delivery/verify.py"))
        .env("WORKSPACES", ws)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root)
        .status()
        .expect("offline315 source/build provenance and physical link checks");
    assert!(status.success(), "Source table check failed; missing source cannot become full delivery");
}
