use std::{path::PathBuf, process::Command};

fn run(selector: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-21-t34-demo61b-video/check_bound.py"))
        .arg(selector)
        .status()
        .expect("run actual T34 Python checks");
    assert!(status.success(), "T34 offline selector failed: {selector}");
}

#[test]
fn demo61b_video_preflight() {
    // Passing this local input check does not satisfy the spec's human review.
    run("preflight");
}

#[test]
fn demo61b_video_negative() {
    run("negative");
}

#[test]
fn demo61b_video_evidence() {
    // Explicit pending evidence structure; no screenshots or device actions.
    run("evidence");
}
