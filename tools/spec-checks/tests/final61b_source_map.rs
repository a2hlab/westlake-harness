use std::path::Path;
use std::process::Command;
#[test]
fn final61b_source_map() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let workspaces = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-13-final61b-source-map/test_sources.py"))
        .env("WORKSPACES",workspaces).env("PYTHONDONTWRITEBYTECODE","1")
        .current_dir(root).status().expect("run offline source mapping/CLI gates");
    assert!(result.success(),"final61b source mapping or originalCLI compatibility failed");
}
