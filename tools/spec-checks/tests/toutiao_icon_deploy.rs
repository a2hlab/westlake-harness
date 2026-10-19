use std::process::Command;
#[test]
fn toutiao_icon_deploy() {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-19-toutiao-icon-deploy/test_deploy.py"))
        .current_dir(&root)
        .status().expect("run deployment transaction tests");
    assert!(status.success(), "deployment transaction checks failed");
}
