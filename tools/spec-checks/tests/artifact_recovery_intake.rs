use std::path::Path;
use std::process::Command;

#[test]
fn artifact_recovery_intake() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    for name in ["test_intake.py", "check_intake.py"] {
        let result = Command::new("python3")
            .arg(root.join("benchmark/2026-10-26-demo-artifact-recovery").join(name))
            .current_dir(&root).status().expect("python3");
        assert!(result.success(), "intake checks failed: {}", name);
    }
}
