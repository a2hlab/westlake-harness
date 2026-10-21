use std::path::Path;
use std::process::Command;

// T35 receipt: three real frames per board with device times >= 2 s apart and verifiable SHAs, raw receipts
// re-hashed when present, no input/click command in any argv, and the verdict never upgrades unknown to a claim.
const CHECK: &str = r#"
import hashlib, json, os, sys
root = sys.argv[1]; d = os.path.join(root, "benchmark/2026-10-21-manual-video-regression")
r = json.load(open(os.path.join(d, "results.json")))
assert r["verdict"]["freeze_reproduced"] is False and r["verdict"]["human_playback_failure"] == "NOT_CLAIMED"
assert "withdrawn" in r["user_update"]
for s in ("5cd", "61b"):
    t = sorted(float(x["device_epoch"]) for x in r["screenshots"] if f"/{s}-" in x["alias"])
    assert len(t) == 3 and all(b - a >= 2 for a, b in zip(t, t[1:])), s
home = os.path.expanduser("~"); n = 0
for x in r["screenshots"] + [y for c in r["command_receipts"] for y in c["raw_refs"]]:
    p = x["alias"].replace("$HOME", home)
    if os.path.exists(p):
        b = open(p, "rb").read(); assert hashlib.sha256(b).hexdigest() == x["sha256"] and len(b) == x["size"]; n += 1
bad = ("uinput", "input tap", "aa start", "power-shell wakeup", "power-shell timeout", "uitest", "keyevent")
for c in r["command_receipts"]:
    assert not any(k in " ".join(c["argv"]) for k in bad), c["id"]
w = json.load(open(os.path.join(d, "whitescreen-01/results.json")))
assert w["guardian_state"]["state"] == "AWAITING_REENTRY" and w["static_mechanism"]["conclusion"].startswith("INFERRED")
assert w["static_mechanism"]["watchdog.sh"]["sha256"].startswith("8bf74a08")
t = sorted(float(x["device_epoch"]) for x in w["screenshots"]); assert len(t) == 3 and all(b - a >= 2 for a, b in zip(t, t[1:]))
for x in w["screenshots"] + [y for c in w["command_receipts"] for y in c["raw_refs"]] + [w["static_mechanism"]["watchdog.sh"], w["static_mechanism"]["reentry-common.sh"]]:
    p = x["alias"].replace("$HOME", home); p = p if os.path.isabs(p) else os.path.join(root, p)
    if os.path.exists(p):
        b = open(p, "rb").read(); assert hashlib.sha256(b).hexdigest() == x["sha256"] and len(b) == x["size"], x["alias"]; n += 1
for c in w["command_receipts"]:
    assert not any(k in " ".join(c["argv"]) for k in bad), c["id"]
print("t35 receipt ok, rehashed", n)
"#;

#[test]
fn toutiao_manual_video_state_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let ok = Command::new("python3").arg("-I").arg("-c").arg(CHECK).arg(&root).status().expect("python3").success();
    assert!(ok, "T35 receipt check failed");
}
