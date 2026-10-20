// T27 buffer-observation selectors. Each scenario selector dispatches the SAME real host test
// (benchmark/2026-10-20-t27-buffer-observation/check.py -> builds + runs test_observer.c, the one
// existing C test that asserts every scenario). No per-scenario test is crafted. Offline, no device.
use std::path::Path;
use std::process::Command;

fn run_host_test() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t27-buffer-observation/check.py"))
        .current_dir(&root)
        .status()
        .expect("run the T27 observer host test (cc + test_observer.c)");
    assert!(status.success(), "T27 observer host test failed");
}

#[test]
fn ttvideo_t27_cpu_observe() { run_host_test(); }

#[test]
fn ttvideo_t27_import_observe() { run_host_test(); }

#[test]
fn ttvideo_t27_unknown() { run_host_test(); }

#[test]
fn ttvideo_t27_bounds() { run_host_test(); }

#[test]
fn ttvideo_t27_durable() { run_host_test(); }

#[test]
fn ttvideo_t27_lifetime() { run_host_test(); }

// The receipt scenario (missing source/tool/raw-log rejection + byte-identical T25 baseline relink +
// check_frozen) is NOT provable by the observer function host test. It is verified ONLY by the final
// T26 joint-production package (cx), which does not yet exist. Ignored (NOT counted as passed) until
// that package's real receipt checker exists; running it with --ignored panics NOT_YET_VERIFIED.
// See benchmark/2026-10-20-t27-buffer-observation/receipt.json (production_receipt: NOT_YET_VERIFIED).
#[test]
#[ignore = "T27 production receipt NOT_YET_VERIFIED: pending the T26 joint-production package (see receipt.json)"]
fn ttvideo_t27_receipt() {
    panic!("T27 production receipt NOT_YET_VERIFIED: pending the T26 joint-production package");
}
