use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_5cd_recovery_offline() {
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 let status=Command::new("python3").arg(root.join("benchmark/2026-10-20-5cd-icon-recovery/test_tool.py"))
  .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("t12 offline tests");
 assert!(status.success());
}
