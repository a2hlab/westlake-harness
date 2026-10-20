use std::{path::PathBuf, process::Command};

fn run(case: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("-B")
        .arg(root.join("benchmark/2026-10-20-evolution-closeout/host-preflight/test_preflight.py"))
        .arg(case)
        .status()
        .expect("python3");
    assert!(status.success(), "real offline HAP preflight cases failed");
}

#[test]
fn host_hap_preflight_positive() { run("positive"); }

#[test]
fn host_hap_preflight_negative() { run("negative"); }
