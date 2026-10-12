// Four narrow offline selectors. Every Python scenario denies subprocess/device calls.
use std::path::PathBuf;
use std::process::Command;
fn run(module: &str, name: &str) {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let output = Command::new("python3")
        .args(["-m", "unittest", &format!("{}.{}", module, name), "-v"])
        .current_dir(root.join("benchmark/2026-10-12-exact-realization"))
        .env("WORKSPACES", root.canonicalize().unwrap().parent().unwrap())
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .output().expect("offline exact realization tests");
    assert!(output.status.success(), "{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr));
}
#[test]
fn exact_realization_roundtrip() { run("test_realization", "RealizationTests.test_roundtrip_actual_full_source_and_exact_v6_package"); }
#[test]
fn exact_realization_reject() { run("test_realization", "RealizationTests.test_reject_bad_pins_unknown_bytes_and_duplicate_assignments"); run("test_source_identity", "SourceIdentityTests"); }
#[test]
fn exact_realization_selfcheck() { run("test_realization", "RealizationTests.test_selfcheck_independent_running_window_and_stale_boot"); run("test_sameboard", "SameBoardTests"); run("test_seal_checks", "SealChecksTests"); }
#[test]
fn exact_realization_restore() { run("test_realization", "RealizationTests.test_restore_preview_and_unchanged_executor_guards"); run("test_entrypoints", "EntrypointTests"); }
