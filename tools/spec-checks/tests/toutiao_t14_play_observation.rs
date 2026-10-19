use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t14_offline() {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status=Command::new("python3")
      .arg(root.join("benchmark/2026-10-20-t14-play-observation/test_observe.py"))
      .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("T14 host checks");
    assert!(status.success());
}
