use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t18b_audiotrack_production() {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    for name in ["test_replay.py","verify.py"] {
        let status=Command::new("python3").arg(root.join("benchmark/2026-10-20-t18-audiotrack-production").join(name))
            .env("PYTHONDONTWRITEBYTECODE","1").current_dir(root).status().expect("T18 production evidence checks");
        assert!(status.success());
    }
}
