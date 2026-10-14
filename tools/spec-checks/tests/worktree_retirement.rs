use std::path::Path;
use std::process::Command;
#[test]
fn worktree_retirement() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for script in ["test_verify.py", "verify.py"] {
        let status = Command::new("python3")
            .arg(root.join("benchmark/2026-10-14-worktree-retirement").join(script))
            .current_dir(&root).status().expect("retirement evidence check");
        assert!(status.success());
    }
}
