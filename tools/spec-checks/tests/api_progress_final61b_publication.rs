use std::path::Path;
use std::process::Command;
#[test]
fn api_progress_final61b_publication() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let ws = std::env::var_os("WORKSPACES").unwrap_or_else(|| root.parent().unwrap().as_os_str().to_owned());
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-api-progress-final61b-publication/test_physical_links.py"))
        .env("WORKSPACES", ws).env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root).status().expect("read-only physical publication seam");
    assert!(status.success(), "Physical publication path/link seam failed");
}
