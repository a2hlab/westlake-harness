use std::process::Command;
fn run(method: &str) {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3").current_dir(&root)
        .arg(root.join("benchmark/2026-10-02-u12-final-assembly/test_final.py"))
        .arg(method).status().expect("Python final U12 check");
    assert!(status.success());
}
#[test] fn u12_final_members() { run("Final.test_members"); }
#[test] fn u12_final_gates() { run("Final.test_gates"); }
#[test] fn u12_final_plans() {
    run("Final.test_plans");
    run("Final.test_finish_order_and_fail_closed");
    run("Final.test_admission_never_arms_or_transports");
}
