use std::path::Path;
use std::process::Command;

fn check(script: &str, mode: Option<&str>) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let mut command = Command::new("python3");
    command.arg(root.join("benchmark/2026-10-03-u15-on-u14-base").join(script));
    if let Some(mode) = mode {
        command.arg(mode);
    }
    let status = command.current_dir(root).status().expect("run cold U15 on U14 checks");
    assert!(status.success());
}

#[test]
fn u15_u14_binding() {
    check("test_binding.py", Some("--binding"));
}

#[test]
fn u15_u14_replay() {
    check("test_binding.py", Some("--replay"));
    check("test_replay_path.py", None);
}
