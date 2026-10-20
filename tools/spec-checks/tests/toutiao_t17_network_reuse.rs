use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t17_network_reuse() {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    for name in ["verify_candidate.py","test_executor.py","test_reader.py","test_collector.py"] {
      let status=Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t17-network-reuse").join(name))
        .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("T17 offline checks");
      assert!(status.success());
    }
}
