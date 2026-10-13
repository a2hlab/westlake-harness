use std::path::Path;
use std::process::Command;
#[test]
fn runtime_surfaceview_split() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let program = root.join("benchmark/2026-10-13-runtime-surfaceview-split/verify.py");
    let workspaces = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3").arg(program).env("WORKSPACES", workspaces)
        .env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root).status().expect("read existing real function/build/ABI receipts");
    assert!(status.success(), "runtime candidate source/build/ABI closure failed");
}
