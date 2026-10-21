use std::path::Path;
use std::process::Command;

// T38 slice 01: read-only fresh receipts target only 61b and never read environ; the derived deploy.py differs
// from the G01 donor by exactly the OLD_ROOT line; the disabled new-ROOT package is refused by prepare
// (startup authority) when present; results never claim a device write or a fix.
const CHECK: &str = r#"
import glob, hashlib, json, os, subprocess, sys, tempfile
root = sys.argv[1]; d = os.path.join(root, "benchmark/2026-10-21-manual-video-regression/host-reentry-window")
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
r = json.load(open(os.path.join(d, "results.json")))
assert r["device_writes"] == 0 and r["rea_calls"] == 0 and r["refused_environ_reads_retried"] == 0
assert "PLAN_PENDING_OUTER" in r["status"] and "SAFETY_STOP_RECORDED" in r["status"] and r["other_boards_touched"] is False
assert r["new_root_package"]["r3_root_reused"] is False and r["new_root_package"]["root"].endswith("icon-manual-20261021-r4c")
assert r["new_root_package"]["pins"]["watchdog.sh"].startswith("c73dadb3") and "STARTUP_ENABLED=0" in r["new_root_package"]["state"]
man = dict(l.split()[::-1] for l in open(os.path.join(d, "package/MANIFEST.sha256")).read().splitlines())
assert h(os.path.join(d, "package/MANIFEST.sha256")) == r["new_root_package"]["manifest_sha256"]
for k, v in r["new_root_package"]["pins"].items(): assert man["payload/" + k] == v, k
for a in glob.glob(os.path.join(d, "fresh-01/*.argv.json")):
    argv = json.load(open(a)); s = " ".join(argv)
    assert "environ" not in s and "5ea34a45" not in s and "rea" not in argv[:1], a
    if "hdc" in argv and "list" not in argv: assert argv[argv.index("-t") + 1] == "61b0657200000000000000000324012c", a
    w = " ".join(argv[argv.index("shell") + 1:]) if "shell" in argv else ""
    assert not any(x in w for x in ("rm ", "mount", "kill", "reboot", "aa start", "uinput", "> /", "sed -i")), a
assert open(os.path.join(d, "fresh-01/f00-held.rc")).read().strip() == "1"
for i, v in r["fresh_01"]["receipt_rc"].items(): assert int(open(os.path.join(d, f"fresh-01/{i}.rc")).read()) == v, i
assert h(os.path.join(d, "fresh-01/61b-fresh-1.jpeg")) == r["fresh_01"]["screenshot"]["sha256"]
assert h(os.path.join(d, "fresh-01/before.cfg")) == r["fresh_01"]["live_cfg_sha256"] == r["transaction"]["before_cfg_sha256"]
donor = os.path.join(root, "benchmark/2026-10-21-t34-demo61b-video/guardian-deployment-01")
a = open(os.path.join(donor, "deploy.py")).read(); b = open(os.path.join(d, "deployment/deploy.py")).read()
assert "OLD_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3'" in b and "('STARTUP_START_PARENT_SHA','real-start-parent-bounded.sh')" in b
assert "def validate(plan, folder, authority=True):" in b and "'startup authority')" in b
assert h(os.path.join(d, "deployment/deploy.py")) == r["deployment_v2"]["deploy.py"] and r["deployment_v2"]["validation"].startswith("UNVALIDATED")
pa = open(os.path.join(donor, "prepare.py")).read().splitlines(); pb = open(os.path.join(d, "deployment/prepare.py")).read().splitlines()
pd = [(x, y) for x, y in zip(pa, pb) if x != y]; assert len(pa) == len(pb) and pd == [("    validate(plan,out)", "    validate(plan,out,authority=False)")], pd
assert not glob.glob(os.path.join(d, "**/test_*.py"), recursive=True)
v = r["fresh_02"]; assert v["all_equal_w05_retained_sha"] and all(x == 0 for x in v["receipt_rc"].values())
assert h(os.path.join(d, "fresh-02/run.sh.before")) == v["run_sh"]["sha256"]
import re as _re; assert hashlib.sha256(_re.sub(rb"(?m)^export WL_PARENT_ID=[0-9]+$", b"export WL_PARENT_ID=<WID>", open(os.path.join(d, "fresh-02/run.sh.before"), "rb").read())).hexdigest() == v["run_sh"]["normalized_sha256"]
assert os.path.exists(os.path.join(d, r["safety_stop"]))
ran = 0
print("t38 slice02 ok (static; prepare not executed)", ran)
"#;

#[test]
fn toutiao_host_reentry_window() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let ok = Command::new("python3").arg("-I").arg("-c").arg(CHECK).arg(&root).status().expect("python3").success();
    assert!(ok, "T38 host reentry window slice check failed");
}
