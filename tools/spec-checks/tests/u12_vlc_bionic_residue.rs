use std::path::Path;
use std::process::Command;

#[test]
fn u12_vlc_bionic_residue() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-vlc-bionic-residue/test_residue.py"))
        .current_dir(root)
        .status()
        .expect("run VLC bionic residue checks");
    assert!(status.success());
}
