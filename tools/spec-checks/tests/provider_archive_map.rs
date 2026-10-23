use std::path::Path;
use std::process::Command;

#[test]
fn provider_archive_map() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .args(["benchmark/2026-10-23-provider-archive-map/check.py", "--self-test"])
        .current_dir(root)
        .output()
        .expect("run G38 offline reference checks");
    assert!(output.status.success(), "{}\n{}",
        String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
