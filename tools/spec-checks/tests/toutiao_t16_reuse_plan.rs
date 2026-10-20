use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t16_reuse_plan() {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status=Command::new("python3")
      .arg(root.join("benchmark/2026-10-20-t15-player-load-reuse/verify_plan.py"))
      .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("T16 static plan checks");
    assert!(status.success());
    let status=Command::new("python3")
      .arg(root.join("benchmark/2026-10-20-t15-player-load-reuse/test_executor.py"))
      .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("T16 host CAS boundary checks");
    assert!(status.success());
}
