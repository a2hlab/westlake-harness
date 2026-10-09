use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-09-local-build-check/check_delivery.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("复核真实本机构建交件");
    assert!(status.success());
}

#[test]
fn local_build_identity() { check("identity"); }
#[test]
fn local_build_owner() { check("owner"); }
#[test]
fn local_build_boat() { check("boat"); }
#[test]
fn local_build_report() { check("report"); }
