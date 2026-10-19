use std::path::Path;
use std::process::Command;

// Spec selector for specs/toutiao-icon-reentry/t1-reentry.spec.md ("测试: toutiao_icon_reentry").
// Transcalls the offline shell checker, which runs the pure WMS parser tests, the
// reentry state-machine tests (final adapter seam contract), and a generator smoke
// test that verifies the members->startup->startup.expected SHA cascade. No device,
// no network, no python/awk. The real-board screenshot scenario stays human-reviewed.
#[test]
fn toutiao_icon_reentry() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap();
    let checker = root.join("benchmark/2026-10-19-toutiao-icon-reentry/tests/run-all.sh");
    assert!(
        checker.exists(),
        "offline checker missing: {}",
        checker.display()
    );
    let status = Command::new("sh")
        .arg(&checker)
        .current_dir(root)
        .status()
        .expect("run offline toutiao icon-reentry parser/state-machine/generator checks");
    assert!(
        status.success(),
        "toutiao icon-reentry offline checks failed; see benchmark/2026-10-19-toutiao-icon-reentry/tests/last-run.log"
    );
}
