//! Offline decision checks only. Actual UI remains human pending_review.
use std::path::Path;
use std::process::Command;
fn check(class: &str) {
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap();
    let status=Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-5cd-icon-readiness/test_collect.py"))
        .arg(class).arg("-v").env("PYTHONDONTWRITEBYTECODE","1")
        .current_dir(root).status().expect("5cd offline checks");
    assert!(status.success(),"5cd {class} failed");
}
#[test] fn ttvideo_5cd_readiness_admission(){check("Admission");}
#[test] fn ttvideo_5cd_readiness_identity(){check("Identity");}
#[test] fn ttvideo_5cd_readiness_receipt(){check("Receipt");}
