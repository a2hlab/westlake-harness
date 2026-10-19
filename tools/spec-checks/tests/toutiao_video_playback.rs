//! Receipt gates only. Actual video/audio/causality require strict human review.
use std::path::Path;
use std::process::Command;

fn receipt(stage: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let python = std::env::var("PYTHON").unwrap_or_else(|_| "python3".into());
    let status = Command::new(python)
        .arg(root.join("benchmark/2026-10-19-toutiao-video-plan/verify_receipt.py"))
        .arg(stage).current_dir(root).env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("execute fail-closed evidence binding check");
    assert!(status.success(), "missing or invalid evidence; human review is still mandatory");
}

#[test]
fn ttvideo_static_receipt() { receipt("static"); }
#[test]
fn ttvideo_build_receipt() { receipt("build"); }
#[test]
fn ttvideo_playback_receipt() { receipt("playback"); }
