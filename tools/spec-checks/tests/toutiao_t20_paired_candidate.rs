use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t20_paired_candidate(){
 let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
 assert!(Command::new("python3").arg(root.join("benchmark/2026-10-20-t20-provider-link-slice/check.py")).current_dir(root).status().expect("real paired host checks").success());
}
