use std::path::Path;
use std::process::Command;
#[test]
fn api_progress_r6_full128() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3").arg(root.join("benchmark/2026-10-13-api-progress-r6-full128/increment.py"))
        .arg("check").env("WORKSPACES", ws).env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root).status().expect("offline scoped API full128 consistency check");
    assert!(status.success(), "Scoped NATIVE-173 full128 API increment failed");
}
