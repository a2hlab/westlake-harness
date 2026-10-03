use std::path::Path;
use std::process::Command;

#[test]
fn sixty_one_b_return_guards() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-03-61b-return/test_return.py"))
        .current_dir(root)
        .status()
        .expect("run mock61b recovery known answers");
    assert!(status.success());
}
