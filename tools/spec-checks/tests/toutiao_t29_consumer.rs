// T29 merged consumer selectors. Logger checks retain the author entry.
// Method selectors run the real pinned TUs + real logger through the independent host fixture.
use std::path::Path;
use std::process::Command;

fn run_consumer_check() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t29-window-observation/consumer/tests/check.py"))
        .current_dir(&root)
        .status()
        .expect("run the T29 consumer check (observe29c host test + derived pins)");
    assert!(status.success(), "T29 consumer check failed");
}

// ---- LOGGER + PINS: locally verified real checks ----

#[test]
fn ttvideo_t29_consumer_budget() { run_consumer_check(); }

#[test]
fn ttvideo_t29_consumer_sink() { run_consumer_check(); }

#[test]
fn ttvideo_t29_consumer_pins() { run_consumer_check(); }

// One actual method execution per Rust test process; all three selectors require that result.
// No persistent PASS cache: each test process starts fresh and verifies the current four source pins.
fn run_consumer_methods() {
    static RESULT: std::sync::OnceLock<Result<(), String>> = std::sync::OnceLock::new();
    let result = RESULT.get_or_init(|| {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let output = Command::new("python3")
            .arg(root.join("benchmark/2026-10-20-t29-consumer-test-peer/run_integrated.py"))
            .current_dir(&root).output().map_err(|e| e.to_string())?;
        if output.status.success() { println!("{}", String::from_utf8_lossy(&output.stdout)); Ok(()) }
        else { Err(format!("{}\n{}", String::from_utf8_lossy(&output.stdout), String::from_utf8_lossy(&output.stderr))) }
    });
    assert!(result.is_ok(), "T29 actual consumer methods failed: {:?}", result);
}

#[test]
fn ttvideo_t29_consumer_calls() { run_consumer_methods(); }
#[test]
fn ttvideo_t29_consumer_invalid() { run_consumer_methods(); }
#[test]
fn ttvideo_t29_consumer_producer() { run_consumer_methods(); }
