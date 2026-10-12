use std::path::PathBuf;
use std::process::Command;

fn check(group: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let result = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-feed-classifier/verify.py"))
        .args(["--group", group])
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(&root)
        .output()
        .expect("run local pinned-image classifier checks");
    assert!(result.status.success(), "{}\n{}", String::from_utf8_lossy(&result.stdout), String::from_utf8_lossy(&result.stderr));
}

#[test]
fn recovery_feed_classifier_positive() { check("positive"); }
#[test]
fn recovery_feed_classifier_negative() { check("negative"); }
#[test]
fn recovery_feed_classifier_reproducible() { check("reproducible"); }
