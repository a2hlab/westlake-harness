use std::path::Path;
use std::process::Command;
#[test]
fn ttvideo_t21_shim_transaction() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    for name in ["test_executor.py", "test_shim.py"] {
        let status = Command::new("python3")
            .arg(root.join("benchmark/2026-10-20-t21-shim-deployment").join(name))
            .env("PYTHONDONTWRITEBYTECODE", "1").current_dir(root)
            .status().expect("T21 actual offline executor tests");
        assert!(status.success());
    }
}
