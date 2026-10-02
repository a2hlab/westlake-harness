use std::path::Path;
use std::process::Command;

#[test]
fn u12_private_zlib() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-private-zlib/test_route.py"))
        .current_dir(root)
        .status()
        .expect("run reviewed private zlib checks");
    assert!(status.success());
}
