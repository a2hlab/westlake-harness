use std::path::Path;
use std::process::Command;

// Minimal receipt check for GENSHIN-T1: six outputs exist, refs carry sha256/size,
// command receipts carry argv/rc/raw_refs, MISSING keeps empty inputs and names the
// unsearched OrbStack/hw248 scope, and nothing claims a runtime verdict. Repo refs are
// re-hashed; private refs are re-hashed only when the private evidence dir exists.
// Evidence quality itself stays human-reviewed (pending_review).
const CHECK: &str = r#"
import hashlib, json, os, re, sys
root = sys.argv[1]
d = os.path.join(root, "benchmark/2026-10-21-genshin-static-intake")
names = ["README.md", "results.json", "input-index.json", "static-matrix.json",
         "boatattack-comparison.json", "source-index.json"]
for n in names:
    assert os.path.isfile(os.path.join(d, n)), "missing " + n
J = {n: json.load(open(os.path.join(d, n))) for n in names[1:]}
res = J["results.json"]
assert res["status"] in ("LOCATED", "PARTIAL", "MISSING"), res["status"]
for k in ("scope", "elapsed", "limits", "unknowns", "next_action"):
    assert k in res and res[k], "results missing " + k
for n in ("results.json", "static-matrix.json", "boatattack-comparison.json"):
    if "runtime_verdict" in J[n]:
        assert J[n]["runtime_verdict"] == "NOT_TESTED", n
assert res["runtime_verdict"] == "NOT_TESTED"
if res["status"] == "MISSING":
    assert J["input-index.json"]["inputs"] == []
    assert J["static-matrix.json"]["rows"] == []
    na = res["next_action"]
    assert "OrbStack" in na and "hw248" in na, "next_action must name unsearched OrbStack/hw248"
priv = os.path.expanduser("~/.local/share/westlake/genshin-static-intake-20261021")
def walk(o):
    if isinstance(o, dict):
        if "alias" in o and "sha256" in o:
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
refs = [r for n in J for r in walk(J[n])]
assert refs, "no refs"
checked = 0
for r in refs:
    assert re.fullmatch(r"[0-9a-f]{64}", r["sha256"]), r
    assert isinstance(r["size"], int) and r["size"] >= 0, r
    a = r["alias"]
    assert not a.startswith("/Users/") and not a.startswith("/home/"), "user-bound path " + a
    if a.startswith("$GENSHIN_T1_PRIVATE/"):
        p = os.path.join(priv, a.split("/", 1)[1])
        if not os.path.isdir(priv):
            continue
    else:
        p = os.path.join(root, a)
    b = open(p, "rb").read()
    assert len(b) == r["size"] and hashlib.sha256(b).hexdigest() == r["sha256"], "ref mismatch " + a
    checked += 1
rec = res["command_receipts"]
assert rec
for c in rec:
    assert isinstance(c["argv"], list) and c["argv"], c["id"]
    assert "rc" in c and c["raw_refs"], c["id"]
    if c["rc"] is None or "INVALID" in c.get("status_note", ""):
        assert c.get("status_note"), "non-clean receipt needs status_note " + c["id"]
for row in J["boatattack-comparison.json"]["rows"]:
    for k in ("input_ref", "observation", "evidence_level", "reuse_condition", "unknown"):
        assert k in row, k
print("genshin_static_intake receipt ok: refs", len(refs), "rehashed", checked, "receipts", len(rec))
"#;

#[test]
fn genshin_static_intake_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("-I")
        .arg("-c")
        .arg(CHECK)
        .arg(&root)
        .status()
        .expect("run GENSHIN-T1 receipt check");
    assert!(status.success());
}
