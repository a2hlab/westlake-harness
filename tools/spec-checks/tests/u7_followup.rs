use std::path::Path;
use std::process::Command;

fn run(script: &str, selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join(script))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run U7 followup evidence tests");
    assert!(status.success());
}

#[test]
fn u7_followup_intake() {
    run("benchmark/2026-10-01-u7-scoring/test_followup.py", "IntakeTests");
}

#[test]
fn u7_followup_scores() {
    run("benchmark/2026-10-01-u7-scoring/test_followup.py", "ScoreTests");
}

#[test]
fn u7_followup_full() {
    run("benchmark/2026-10-01-u7-scoring/test_followup.py", "FullTests");
}

#[test]
fn trampoline_rules() {
    run("benchmark/2026-10-01-trampoline-scan/test_scan.py", "RuleTests");
}

#[test]
fn trampoline_replay() {
    run("benchmark/2026-10-01-trampoline-scan/test_scan.py", "ReplayTests");
}
