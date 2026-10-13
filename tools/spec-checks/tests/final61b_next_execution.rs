use std::path::Path;
use std::process::Command;
#[test]
fn final61b_next_execution() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3").arg(root.join("benchmark/2026-10-14-final61b-next-execution/check.py"))
        .env("WORKSPACES", ws).env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root)
        .status().expect("offline61b original parameter and input audit");
    assert!(status.success(), "Final61b original successor parameters failed");
}
