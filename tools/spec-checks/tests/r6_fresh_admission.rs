use std::path::Path;
use std::process::Command;
#[test]
fn r6_fresh_admission() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let test = root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-fresh-admission/test_binding.py");
    let status = Command::new("python3").arg(test).env("WORKSPACES", ws)
        .env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root).status().expect("offline fresh admission checks");
    assert!(status.success(), "fresh admission checks failed");
}
