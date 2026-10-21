use std::path::Path;
use std::process::Command;

// Receipt check for COMMERCIAL-G05: fresh state keeps boot before/after from this run's receipts (not a
// historical baseline), lock holder, system/resources and host identity; device writes are 0; the plan is
// disabled, names its board_run entry, rollback and 1200 s stop, and lists unknowns; every receipt keeps
// argv/rc/raw_refs with failures classed; public files hold no user-bound paths. Repo refs are re-hashed;
// private refs only when the private dir exists. Evidence quality stays human-reviewed.
const CHECK: &str = r#"
import hashlib, json, os, re, sys
root = sys.argv[1]
d = os.path.join(root, "benchmark/2026-10-21-commercial-game/spare-preflight")
for n in ("README.md", "results.json"):
    assert os.path.isfile(os.path.join(d, n)), n
res = json.load(open(os.path.join(d, "results.json")))
assert res["token"] == "COMMERCIAL-G05" and res["runtime_verdict"] == "NOT_TESTED" and res["device_writes"] == 0
f = res["fresh"]
assert f["serial"] == "5ea34a4500000000000000001123012c"
for k in ("boot_id_before", "boot_id_after"):
    assert re.fullmatch(r"[0-9a-f-]{36}", f[k]), k
ids = {c["id"]: c for c in res["command_receipts"]}
assert "q01-boot-before" in ids and "q10-boot-after" in ids and ids["q01-boot-before"]["rc"] == 0 and ids["q10-boot-after"]["rc"] == 0
assert "historical" in f["runtime_deploy"]["last_recorded_fp"]["source"].lower() or "NOT fresh" in f["runtime_deploy"]["last_recorded_fp"]["source"]
for k in ("lock_note", "system", "memory_kB", "data_partition", "host_parent_child", "genshin_installed"):
    assert k in f, k
p = res["plan"]
assert p["execution_enabled"] is False and "board_run.py" in p["entry"] and p["rollback"] and p["unknown"]
plan = json.load(open(os.path.join(d, "plan/board-run-genshin-5ea.disabled.json")))
assert plan["execution_enabled"] is False and plan["serial"] == f["serial"] and plan["stop_new_tests_by_minute"] * 60 == 1200
assert isinstance(plan["before_unlock"], list) and all(isinstance(x, str) for x in plan["before_unlock"])
assert "61b" not in plan["serial"]
priv = os.path.expanduser("~/.local/share/westlake/commercial-game-20261021/spare-preflight")
checked = 0
for r in p["files"]:
    b = open(os.path.join(root, r["alias"]), "rb").read()
    assert hashlib.sha256(b).hexdigest() == r["sha256"] and len(b) == r["size"], r["alias"]; checked += 1
for c in res["command_receipts"]:
    assert c["argv"] and c["raw_refs"] and "rc" in c and c["class"] and c["status_note"], c["id"]
    if c["rc"] != 0:
        assert c["class"] in ("FAILED_KEPT", "INVALID_LOCAL", "EXPECTED_REFUSAL"), c["id"]
    assert all("/Users/" not in a for a in c["argv"]), c["id"]
    for r in c["raw_refs"]:
        assert r["alias"].startswith("$COMMERCIAL_G05_PRIVATE/raw/")
        if os.path.isdir(priv):
            b = open(os.path.join(priv, r["alias"].split("/", 1)[1]), "rb").read()
            assert hashlib.sha256(b).hexdigest() == r["sha256"] and len(b) == r["size"], r["alias"]; checked += 1
for n in ("README.md", "results.json"):
    assert "/Users/" not in open(os.path.join(d, n)).read(), n
print("commercial_game_spare_preflight receipt ok: receipts", len(res["command_receipts"]), "rehashed", checked)
"#;

#[test]
fn commercial_game_spare_preflight_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("-I")
        .arg("-c")
        .arg(CHECK)
        .arg(&root)
        .status()
        .expect("run COMMERCIAL-G05 receipt check");
    assert!(status.success(), "COMMERCIAL-G05 receipt check failed");
}
