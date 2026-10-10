use std::path::Path;
use std::process::Command;

#[test]
fn board_state_readonly() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("scripts/lab/test_board_state.py"))
        .arg("-v")
        .current_dir(root)
        .status()
        .expect("run fixture-only board snapshot and evidence integrity checks");
    assert!(status.success());
    println!("OFFLINE_ONLY: mock transport, no HDC/VM/SSH or board lock");
}
