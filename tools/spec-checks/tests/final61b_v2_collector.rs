use std::path::Path;
use std::process::Command;
#[test]
fn final61b_v2_collector() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3").arg(root.join("benchmark/2026-10-14-final61b-v2-collector/preview.py"))
        .env("WORKSPACES", ws).env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root)
        .status().expect("original snapshot parameter preview without device transport");
    assert!(status.success(), "Original V2 collector parameter preview failed");
}
