use std::path::PathBuf;
use std::process::Command;

#[test]
fn toutiao_host_launch_observation() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .arg(root.join("benchmark/2026-10-22-toutiao-host-launch-observation/check_candidate.py"))
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(&root)
        .output()
        .expect("run T39 offline production callback and provenance checks");
    assert!(output.status.success(), "{}\n{}",
        String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
    print!("{}", String::from_utf8_lossy(&output.stdout));
}
