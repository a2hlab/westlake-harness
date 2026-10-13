use std::path::Path;
use std::process::Command;
#[test]
fn r6_serial_dispatch() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let test = root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-serial-dispatch/test_dispatch.py");
    let status = Command::new("python3").arg(test).env("WORKSPACES", ws)
        .env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root).status().expect("offline original entry mock checks");
    assert!(status.success(), "serial dispatch checks failed");
}
