use std::path::Path;
use std::process::Command;
#[test]
fn api_progress_r6() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let test = root.join("benchmark/2026-10-13-api-progress-r6/increment.py");
    let status = Command::new("python3").arg(test).arg("check").env("WORKSPACES", ws)
        .env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root).status().expect("offline one-row API atlas check");
    assert!(status.success(), "R6 API increment consistency failed");
}
