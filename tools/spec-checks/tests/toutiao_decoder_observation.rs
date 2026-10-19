//! R10 offline source/host behavior/negative receipt checks; never deployment.
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent().unwrap().parent().unwrap().to_path_buf()
}
fn verify(mode: &str) {
    let repo = root();
    let status = Command::new(std::env::var("PYTHON").unwrap_or_else(|_| "python3".into()))
        .arg(repo.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r10/verify.py"))
        .arg(mode).current_dir(&repo).env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("execute r10 offline checker");
    assert!(status.success(), "r10 {mode} failed");
}
#[test]
fn ttvideo_decoder_observation_source() { verify("source"); }
#[test]
fn ttvideo_decoder_observation_receipt() { verify("receipt-tests"); }
#[test]
fn ttvideo_decoder_observation_forwarding() {
    let repo = root();
    let dir = repo.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r10");
    let persistent = std::env::var_os("WESTLAKE_TEST_ARTIFACTS")
        .map(PathBuf::from).unwrap_or_else(|| dir.join(".artifacts"));
    let nonce = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    let output = persistent.join(format!("host-{}-{nonce}", std::process::id()));
    let status = Command::new(std::env::var("PYTHON").unwrap_or_else(|_| "python3".into()))
        .arg(dir.join("oracle/run.py")).arg("--source").arg(dir.join("ttplayer_log_mirror.c"))
        .arg("--out").arg(&output).current_dir(&repo)
        .env("PYTHONDONTWRITEBYTECODE", "1").status().expect("run real host oracle");
    eprintln!("R10 host evidence: {}", output.display());
    assert!(status.success(), "r10 forwarding/concurrency failed");
}
