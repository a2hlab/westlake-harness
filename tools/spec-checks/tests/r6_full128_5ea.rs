use std::path::Path;
use std::process::Command;
#[test]
fn r6_full128_5ea() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let program = root.join("benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/r6-full128-5ea/test_r6.py");
    let workspaces = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3").arg(program).env("WORKSPACES",workspaces)
        .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("R6 original5ea static prepare guard checks");
    assert!(status.success(),"R6 disabled full128/identity checks failed");
}
