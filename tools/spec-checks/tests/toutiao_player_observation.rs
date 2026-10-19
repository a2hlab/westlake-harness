//! Offline observation behavior only; this does not admit deployment or playback.
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[test]
fn ttvideo_observation_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let status = Command::new(std::env::var("PYTHON").unwrap_or_else(|_| "python3".into()))
        .arg(
            root.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r8/verify_receipt.py"),
        )
        .current_dir(root)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .status()
        .expect("verify actual offline build and source receipts");
    assert!(
        status.success(),
        "offline source/build receipt binding failed"
    );
}

#[test]
fn ttvideo_observation_derivation() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let status =
        Command::new(std::env::var("PYTHON").unwrap_or_else(|_| "python3".into()))
            .arg(root.join(
                "benchmark/2026-10-19-toutiao-video-playback/candidate-r8/verify_derivation.py",
            ))
            .current_dir(root)
            .env("PYTHONDONTWRITEBYTECODE", "1")
            .status()
            .expect("execute exact ELF derivation CLI checks");
    assert!(
        status.success(),
        "ELF derivation or refusal behavior failed"
    );
}

#[test]
fn ttvideo_observation_forwarding() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let persistent = std::env::var_os("WESTLAKE_TEST_ARTIFACTS")
        .map(PathBuf::from)
        .unwrap_or_else(|| {
            PathBuf::from(
                std::env::var_os("HOME").expect("HOME or WESTLAKE_TEST_ARTIFACTS required"),
            )
            .join(".local/share/westlake/spec-checks")
        });
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let output = persistent.join(format!("ttvideo-forwarding-{}-{nonce}", std::process::id()));
    let python = std::env::var("PYTHON").unwrap_or_else(|_| "python3".into());
    let status = Command::new(python)
        .arg(root.join("benchmark/2026-10-19-toutiao-rea-methods/video-1919-player-observation-contract-review/independent-tests/run.py"))
        .arg("--source")
        .arg(root.join("benchmark/2026-10-19-toutiao-video-playback/candidate-r8/ttplayer_log_mirror.c"))
        .arg("--out").arg(&output)
        .current_dir(root).env("PYTHONDONTWRITEBYTECODE", "1")
        .status().expect("execute independent host behavior oracle");
    eprintln!("Host oracle artifacts: {}", output.display());
    assert!(
        status.success(),
        "host forwarding behavior failed; see persistent raw receipts"
    );
}
