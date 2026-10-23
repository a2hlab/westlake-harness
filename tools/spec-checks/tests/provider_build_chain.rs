use std::path::Path;
use std::process::Command;

#[test]
fn provider_build_chain() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .args(["benchmark/2026-10-23-provider-build-chain/check.py", "--self-test"])
        .current_dir(root)
        .output()
        .expect("run bounded offline provider evidence checks");
    assert!(result.status.success(), "{}\n{}",
        String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr));
}
