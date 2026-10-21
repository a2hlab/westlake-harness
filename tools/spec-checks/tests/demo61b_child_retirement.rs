use std::path::Path;
use std::process::Command;

// Spec selector for specs/demo61b-video-delivery/t3-confirmed-child-retirement.spec.md
// ("测试: demo61b_child_retirement"). Thin entry: runs the offline shell tests that source
// the actual r3 watchdog (6 classes), then the same tests against the deployed r2 as a
// negative control, which must fail (r2 has no retirement). No device, no network.
// Human-reviewed scenarios stay pending_review.
#[test]
fn demo61b_child_retirement() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let tests = "benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/tests/run-retirement-tests.sh";
    let r3 = Command::new("sh")
        .arg(tests)
        .current_dir(&root)
        .status()
        .expect("run r3 retirement tests");
    assert!(r3.success(), "r3 retirement tests failed");
    let r2 = Command::new("sh")
        .arg(tests)
        .env(
            "RETIRE_UNDER_TEST",
            "benchmark/2026-10-19-toutiao-icon-reentry/src/watchdog-reentry.sh",
        )
        .current_dir(&root)
        .output()
        .expect("run r2 negative control");
    assert_eq!(r2.status.code(), Some(1), "r2 negative control must fail the retirement checks");
}
