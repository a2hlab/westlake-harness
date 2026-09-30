use std::path::Path;
use std::process::Command;

fn run(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-01-first-frame-suspects/test_scan.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("replay first-frame evidence and independent negative controls");
    assert!(status.success());
}

#[test]
fn first_frame_scope() {
    run("ScopeTests");
}

#[test]
fn first_frame_terminal() {
    run("TerminalTests");
}

#[test]
fn first_frame_rule() {
    run("RuleTests");
}

#[test]
fn first_frame_replay() {
    run("ReplayTests");
}
