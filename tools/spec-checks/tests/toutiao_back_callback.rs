use std::path::Path;
use std::process::Command;
#[test]
fn toutiao_back_callback() {
 let repo=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 let r=Command::new("python3").arg(repo.join("benchmark/2026-10-14-toutiao-manual-repair/back-callback-overlay/test_overlay.py")).current_dir(repo).output().expect("offline callback checks");
 assert!(r.status.success(),"{}\n{}",String::from_utf8_lossy(&r.stdout),String::from_utf8_lossy(&r.stderr));
}
