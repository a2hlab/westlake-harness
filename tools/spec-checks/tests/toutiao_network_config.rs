//! Exact offline r9 inputs only; no board admission or playback verdict.
use std::path::Path;
use std::process::Command;

#[test]
fn ttvideo_network_config_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status = Command::new(std::env::var("PYTHON").unwrap_or_else(|_| "python3".into()))
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r9/verify_config.py"))
        .current_dir(root).env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("verify exact configuration and reused binary inputs");
    assert!(status.success(), "r9 input/configuration drift; not a playback check");
}
