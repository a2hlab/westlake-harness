use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t18c_observer_outer() {
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 let status=Command::new("python3").arg(root.join("benchmark/2026-10-20-t18-observer-outer/test_wrapper.py")).env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("outer host checks");
 assert!(status.success());
}
