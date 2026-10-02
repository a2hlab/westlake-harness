use std::path::Path;
use std::process::Command;

fn check(selector: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-02-u12-upstream-audio/test_audio.py"))
        .arg(selector)
        .current_dir(root)
        .status()
        .expect("run offline U12 audio tests");
    assert!(status.success());
}

#[test]
fn u12_audio_architecture() {
    check("ArchitectureTests");
}

#[test]
fn u12_audio_primitives() {
    check("PrimitiveTests");
}

#[test]
fn u12_audio_static_gates() {
    check("StaticGateTests");
}
