use std::path::Path;
use std::process::Command;

// T36: re-run the r4 production-function replay and the unchanged r3 suite against r4, then check
// results.json: candidate/receipt SHAs, read-only sources unchanged, and gaps not upgraded to claims.
const CHECK: &str = r#"
import hashlib, json, os, subprocess, sys
root = sys.argv[1]; d = os.path.join(root, "benchmark/2026-10-21-manual-video-regression/host-reentry-candidate")
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
def run(*a):
    p = subprocess.run(["sh", *a], cwd=d, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout.strip().splitlines()[-1]
assert run("tests/run-epoch-tests.sh") == (0, "140 passed, 0 failed")
rc, last = run("tests/run-r3-suite-on-r4.sh"); assert rc == 0 and last.startswith("R3_ON_R4 OK"), last
assert run(os.path.join(root, "benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/tests/run-retirement-tests.sh")) == (0, "71 passed, 0 failed")
r = json.load(open(os.path.join(d, "results.json")))
assert r["device_actions"] == 0 and r["rea_calls"] == 0 and r["refused_environ_reads_retried"] == 0
assert "NOT_DEPLOYED" in r["status"] and r["root_cause_status"].startswith("INFERRED")
assert run("tests/run-epoch-tests-r4b.sh") == (0, "228 passed, 0 failed")
revs = {x["rev"]: x for x in r["revisions"]}; assert revs["r4"]["verdict"].startswith("REJECTED")
assert h(os.path.join(d, "src/watchdog-reentry-r4c.sh")) == revs["r4c"]["watchdog_sha256"]
pk = os.path.join(d, "candidate-package-r4c"); cp = r["candidate_package"]
assert cp["approved"] is False and cp["startup_enabled"] == 0
assert h(os.path.join(pk, "payload/watchdog.sh")) == revs["r4c"]["watchdog_sha256"] == cp["watchdog_sha256"]
assert h(os.path.join(pk, "MANIFEST.sha256")) == cp["manifest_sha256"]
man = [l.split() for l in open(os.path.join(pk, "MANIFEST.sha256")).read().splitlines()]
assert len(man) == cp["payload_files"] == 22
for s_, f in man: assert h(os.path.join(pk, f)) == s_, f
env = open(os.path.join(pk, "payload/startup.env")).read()
assert "STARTUP_ENABLED='0'" in env and cp["startup_env_sha256"] in open(os.path.join(pk, "payload/startup.expected.sha256")).read()
assert cp["watchdog_sha256"] in open(os.path.join(pk, "payload/entry.sh")).read()
for x in list(r["candidate"].values()) + list(r["sources_read_only"].values()):
    p = os.path.join(d, x["path"]); assert h(p) == x["sha256"] and os.path.getsize(p) == x["size"], x["path"]
assert r["sources_read_only"]["watchdog-reentry-r3.sh"]["sha256"].startswith("8bf74a08")
home = os.path.expanduser("~"); n = 0
for c in r["receipts"]:
    assert c["rc"] == 0, c["id"]; p = os.path.join(d, c["copy"]["path"]); assert h(p) == c["copy"]["sha256"], c["id"]
    o = c["original_alias"].replace("$HOME", home)
    if os.path.exists(o): assert h(o) == c["original_sha256"], c["id"]; n += 1
assert any("NOT claimed" in g for g in r["hard_precondition_gaps"]) and len(r["hard_precondition_gaps"]) >= 5 and any("never observed" in g for g in r["hard_precondition_gaps"])
for v in ("r4", "r4b", "r4c"):
    src = open(os.path.join(d, f"src/watchdog-reentry-{v}.sh")).read()
    assert src.count("kill -15") == 1 and 'rc_send_term() { kill -15 "$1"; }' in src, v
src = open(os.path.join(d, "src/watchdog-reentry-r4c.sh")).read()
assert "rb_owned_pids" not in src and "runid=" in src
assert src.count("kill -15") == 1 and 'rc_send_term() { kill -15 "$1"; }' in src
print("t36 candidate ok, originals rehashed", n)
"#;

#[test]
fn toutiao_host_reentry_candidate() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let ok = Command::new("python3").arg("-I").arg("-c").arg(CHECK).arg(&root).status().expect("python3").success();
    assert!(ok, "T36 host reentry candidate check failed");
}
