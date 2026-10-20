use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t23_egl_import() {
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-20-t23-egl-import/check.py")).current_dir(root).status().expect("actual EGL host checks").success());
}
