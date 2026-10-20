// T29 consumer-observation selectors (agent-spec `测试:` -> Rust test -> real checker). Offline, no
// device, no REA. Two classes of scenario:
//
//  * LOGGER + PINS (CC owns, verified locally): _budget / _sink / _pins all dispatch the ONE real host
//    check (benchmark/2026-10-20-t29-window-observation/consumer/tests/check.py), which builds and runs
//    test_observe29c.c across all 14 modes (8-thread x 10000 concurrency, reserved 30-invalid + disjoint
//    FINAL_EXHAUSTION, 3104/2383872B caps, exhausted hot-path format/time/write == 0, real closed-reader
//    pipe with NO SIGPIPE, owned dev/ino sink that ignores fd2 rebinds, one-write-no-retry EPIPE/EINTR/
//    short-write losses, errno-neutral emit, bounded <768B line) AND verifies the derived baseline is
//    byte-identical to the pinned originals (ttvideo_t29_consumer_pins).
//
//  * METHOD-BODY COMPARISON (base5 integration fixture, pending): _calls / _invalid / _producer require
//    executing the REAL derived JNI method bodies against OH/JNI provider doubles and comparing call
//    count/order/return/errno/exception + recorded fields. That fixture is owned by the independent
//    base5 task (../westlake-harness-api-progress-peer/benchmark/2026-10-20-t29-consumer-test-peer/
//    replay.py) and runs against THIS tree's consumer/derived sources; the unified package lands in
//    mainline. Until then these are NOT_YET_VERIFIED here (running with --ignored panics), so this tree
//    never impersonates the method comparison as passed. See consumer/DELIVERY.md for the exact
//    replay.py invocation and source pins.
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

// ---- METHOD-BODY COMPARISON: base5 integration fixture, NOT_YET_VERIFIED in this tree ----

#[test]
#[ignore = "T29 method comparison NOT_YET_VERIFIED here: base5 replay.py runs the real derived bodies \
            vs OH/JNI doubles against consumer/derived; unified package lands in mainline (DELIVERY.md)"]
fn ttvideo_t29_consumer_calls() {
    panic!("T29 attach/detach/update method comparison runs in the base5 integration fixture \
            (replay.py --consumer-source-dir consumer/derived); not re-implemented in this tree");
}

#[test]
#[ignore = "T29 method comparison NOT_YET_VERIFIED here: base5 replay.py (invalid/released safe \
            early-return of the real derived bodies); unified package lands in mainline (DELIVERY.md)"]
fn ttvideo_t29_consumer_invalid() {
    panic!("T29 invalid/released early-return method comparison runs in the base5 integration fixture; \
            not re-implemented in this tree");
}

#[test]
#[ignore = "T29 method comparison NOT_YET_VERIFIED here: base5 replay.py (TextureView producer \
            replace/destroy ref-rule preservation + old->new correlation); mainline (DELIVERY.md)"]
fn ttvideo_t29_consumer_producer() {
    panic!("T29 producer replace/destroy method comparison runs in the base5 integration fixture; \
            not re-implemented in this tree");
}
