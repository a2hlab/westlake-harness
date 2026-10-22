use std::path::PathBuf;
use std::process::Command;

// T42: validate the ordinary-launch-request observation on 5cd as a FAILURE that was recorded completely and
// recovered, NOT as a task pass. The read-only checker (no device commands) asserts: three automated_request
// `aa start` calls all refused with 10107101 (shell rc0 != success), the host never launched, callback_status
// unknown (path not reached, no onNewWant claim), identity unchanged (public bm-dump fields only), b189 restored
// with the candidate never running, a runtime/native fingerprint NOT claimed, data-dir scoped to UID/GID, no
// screenshot committed; and drives the real check() to refuse forged success / fabricated callback / wrong
// observed_absent framing / identity drift / disk-only recovery / a checker that marks the task pass.
#[test]
fn toutiao_host_observer_device() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let out = Command::new("python3").arg("-B")
        .arg(root.join("benchmark/2026-10-22-toutiao-host-observer-device/check_observation.py"))
        .output().expect("run T42 observation checker");
    assert!(out.status.success(), "{}\n{}", String::from_utf8_lossy(&out.stdout), String::from_utf8_lossy(&out.stderr));
}
