use std::path::Path;
use std::process::Command;
fn run(file: &str, groups: &[&str]) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-12-recovery-executor/tests").join(file))
        .args(groups).current_dir(root).status().expect("offline executor checks");
    assert!(status.success(), "recovery executor selector failed");
}
#[test] fn recovery_executor_plan() { run("test_executor.py", &["PlanTests"]); run("test_cfg_stop.py", &["CFGTests"]); }
#[test] fn recovery_executor_reject() { run("test_executor.py", &["RejectTests", "FailureTests"]); run("test_cfg_stop.py", &["StopTests"]); }
#[test] fn recovery_executor_format() { run("test_executor.py", &["FormatTests"]); }
#[test] fn recovery_executor_autoboot() { run("test_autoboot.py", &[]); }
