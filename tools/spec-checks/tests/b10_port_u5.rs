use std::path::Path;
use std::process::Command;

fn run(path: &str, selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join(path))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline portability and scoring tests");
    assert!(status.success());
}

#[test]
fn b10_port_relocation() {
    run(
        "benchmark/2026-10-01-b10-path-port/test_port.py",
        "RelocationTests",
    );
}

#[test]
fn b10_port_preservation() {
    run(
        "benchmark/2026-10-01-b10-path-port/test_port.py",
        "PreservationTests",
    );
}

#[test]
fn u5_score_identity() {
    run(
        "benchmark/2026-09-30-u4-sweep/j6n4-scoring/test_scoring.py",
        "IdentityTests",
    );
}

#[test]
fn u5_score_decisions() {
    run(
        "benchmark/2026-09-30-u4-sweep/j6n4-scoring/test_scoring.py",
        "DecisionTests",
    );
}
