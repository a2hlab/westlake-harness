// T30 resource-free Request-failure recovery selectors (agent-spec `测试:` -> Rust test -> real checker).
// Offline, no device, no REA. Each scenario dispatches benchmark/2026-10-20-t30-request-recovery/tests/
// check.py, which reuses the PEER'S real route replay (replay.py: the derived window_module.c /
// provider_adapter.c compiled into the actual pair/geometry/R14/R15/R26/entry chain) and the PEER'S real
// pthread pollution counter-example (adapter_pollution.c: the actual r15_adapter). No mirror implementation
// and no value-assertion stand-in. t1 contract revision 2271d5d1f.
//
//   ttvideo_t30_request_recovery  (scenarios 1+2) -- machine: real-route recovery (first=-5,second=0,
//       request_calls=2, retained=0) + baseline poison contrast (second=-16) + concurrent reservation
//       (a flush/abort polluting the RESERVED record during the unlocked provider call keeps it; -EBUSY).
//   ttvideo_t30_retained          (scenarios 3+4) -- machine: concurrent pollution keeps the FAILED
//       record (after_record_rc=0, second=-16, no wrongful clear); the "cleared" wrongful outcome fails.
//   ttvideo_t30_success_regression(scenario 5)    -- machine: the original route cases (rgb/rgbx/yv12/
//       request/map/handle/convert/layout) still PASS through the derived TUs.
//   ttvideo_t30_runtime_evidence  (scenario 6)    -- HUMAN: real-device before/after frames are
//       outer-reviewed; no host test substitutes. #[ignore], pendingreview (zero device here).
//
// The route replay + pollution landed in the main tree (89058228d7), so check.py defaults to the
// SAME-REPO paths under REPO_ROOT (benchmark/2026-10-20-t30-recovery-peer + the T29 shim); WL_T30_PEER_DIR
// / WL_T30_MAIN_REPO override them (e.g. a pre-merge branch pointing at the landed checkout). When the
// real harness is absent the machine tests report a clear setup error (exit 2), never a false pass.
// The recovery-path owner_release-failure counter-example is this tree's own real test
// (benchmark/2026-10-20-t30-request-recovery/test/test_recovery_release_fail.c) compiled into the actual
// pair/geometry/R20/R26 chain with the derived TUs.
use std::path::Path;
use std::process::Command;

fn run(scenario: &str) {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg(root.join("benchmark/2026-10-20-t30-request-recovery/tests/check.py"))
        .arg(scenario)
        .current_dir(&root)
        .status()
        .expect("run the T30 acceptance check (peer replay + pollution against the derived TUs)");
    assert!(status.success(), "T30 {scenario} acceptance failed");
}

#[test]
fn ttvideo_t30_request_recovery() { run("request_recovery"); }

#[test]
fn ttvideo_t30_retained() { run("retained"); }

#[test]
fn ttvideo_t30_success_regression() { run("success_regression"); }

// Scenario 6 is `审核: human`: real on-device before/after dynamic-frame evidence, bound to clip+child,
// is outer-reviewed and cannot be established by any host test (host-only pass != device recovery; and if
// the device never hits the target Q failure, only the window-switch result is proven). NOT a machine
// pass: ignored, pendingreview. Running with --ignored panics; check.py runtime_evidence returns 3.
#[test]
#[ignore = "T30 runtime_evidence is 审核: human — real-device before/after frames, outer-reviewed; \
            no host test substitutes (pendingreview, zero device)"]
fn ttvideo_t30_runtime_evidence() {
    panic!("T30 runtime_evidence HUMAN_PENDINGREVIEW: real-device before/after dynamic frames are \
            outer-reviewed; host-only pass does not prove device recovery");
}
