use std::{path::PathBuf,process::Command};
fn run(case: &str) {
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status=Command::new("python3").arg(root.join("benchmark/2026-10-20-toutiao-launcher-page/test_candidate.py")).arg(case).arg("-v").status().expect("python3");
    assert!(status.success(), "offline launcher closure/refusal test failed");
}
#[test] fn launcher_page_closure(){run("ClosureTests");}
#[test] fn launcher_page_negative(){run("RefusalTests");}
