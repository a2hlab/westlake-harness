use std::path::Path;
use std::process::Command;

#[test]
fn artifact_remote_recovery() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for name in ["test_artifact_fetch.py", "test_artifact_publish.py"] {
        let result = Command::new("python3")
            .arg(root.join("scripts/lab/tests").join(name))
            .current_dir(&root).status().expect("python3");
        assert!(result.success(), "artifact transport tests failed: {}", name);
    }
}
