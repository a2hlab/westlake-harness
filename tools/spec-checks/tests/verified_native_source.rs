use std::path::Path;
use std::process::Command;

#[test]
fn verified_native_source() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-14-verified-source-closeout/native/test_native_source.py"))
        .arg("-v")
        .current_dir(&root)
        .status()
        .expect("run locked native source and dependency known answers");
    assert!(status.success());
    println!("SOURCE-CLOSEOUT: dependency and source tests only; historical production claims remain independently scoped");
}
