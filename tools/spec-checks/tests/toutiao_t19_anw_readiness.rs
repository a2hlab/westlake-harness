use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t19_anw_readiness(){
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-20-t19-anw-integration-readiness/check.py")).current_dir(root).status().expect("readiness evidence").success());
}
