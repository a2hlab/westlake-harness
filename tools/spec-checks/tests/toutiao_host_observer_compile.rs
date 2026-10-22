use std::path::PathBuf;
use std::process::Command;

// T40: validate the exact es2abc compile receipt (no compile/device/sign). Baseline ABC reproduces the
// historical HAP member bb1eccd3 byte-for-byte, the fc0 candidate is byte-identical across two runs, all rc
// are 0, every pinned raw receipt is present and SHA-stable, and the rejectors refuse mismatch/missing/failure.
#[test]
fn toutiao_host_observer_compile() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-22-toutiao-host-observer-compile/check_compile.py"))
        .arg("--negatives")
        .output().expect("run T40 compile checker");
    assert!(out.status.success(), "{}\n{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
