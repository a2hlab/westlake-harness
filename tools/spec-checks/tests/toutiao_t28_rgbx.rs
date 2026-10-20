use std::{path::PathBuf, process::Command};
fn actual(suite: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let r = Command::new("python3").arg(root.join("benchmark/2026-10-20-t28-rgbx/check.py")).args(["--suite",suite]).output().expect("actual T28 evidence check");
    assert!(r.status.success(),"{}\n{}",String::from_utf8_lossy(&r.stdout),String::from_utf8_lossy(&r.stderr));
}
#[test] fn ttvideo_t28_route(){actual("route");}
#[test] fn ttvideo_t28_regression(){actual("regression");}
#[test] fn ttvideo_t28_failures(){actual("failures");}
#[test] fn ttvideo_t28_concurrency(){actual("concurrency");}
#[test] fn ttvideo_t28_build(){actual("build");}
