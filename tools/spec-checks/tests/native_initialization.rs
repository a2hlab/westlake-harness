use std::path::Path;
use std::process::Command;

fn check(case: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .args([
            "benchmark/2026-09-29-static-wall-prediction/test_native_initialization.py",
            case,
        ])
        .current_dir(root)
        .status()
        .expect("run native initialization checks");
    assert!(status.success());
}

#[test]
fn native_initialization_namespace() {
    check("NamespaceTests");
}

#[test]
fn native_initialization_jni_order() {
    check("JniTests");
}

#[test]
fn native_initialization_provenance() {
    check("ProvenanceTests");
}
