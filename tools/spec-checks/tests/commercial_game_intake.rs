use std::path::Path;
use std::process::Command;

// Minimal receipt check for COMMERCIAL-G01: four contract outputs exist; status is one of
// LOCATED/PARTIAL/MISSING with runtime NOT_TESTED; every source row has a MISSING/INACCESSIBLE/
// NOT_SEARCHED-style state; MISSING keeps an empty input index and no install command; receipts
// carry argv/rc/raw_refs and non-clean ones a class+note; public refs/argv have no user-bound
// paths or raw IPs. Repo refs are re-hashed; private refs only when the private dir exists.
// The two manifest evidence layers (APK AndroidManifest vs XAPK container manifest.json) stay
// distinct and tool sources carry their private-original hashes.
// Evidence quality stays human-reviewed (pending_review).
const CHECK: &str = r#"
import hashlib, json, os, re, sys
root = sys.argv[1]
d = os.path.join(root, "benchmark/2026-10-21-commercial-game/intake")
names = ["README.md", "results.json", "input-index.json", "source-index.json"]
for n in names:
    assert os.path.isfile(os.path.join(d, n)), "missing " + n
J = {n: json.load(open(os.path.join(d, n))) for n in names[1:]}
res, idx, src = J["results.json"], J["input-index.json"], J["source-index.json"]
assert res["token"] == "COMMERCIAL-G01"
assert res["status"] in ("LOCATED", "PARTIAL", "MISSING"), res["status"]
assert res["runtime_verdict"] == "NOT_TESTED" and idx["runtime_verdict"] == "NOT_TESTED"
for k in ("scope", "elapsed", "limits", "unknowns", "next_action", "install_tiers", "command_receipts"):
    assert k in res and res[k], "results missing " + k
states = {s["state"] for s in src["sources"]}
ok = {"LOCATED", "PARTIAL", "MISSING", "MISSING_ROOT", "INACCESSIBLE", "NOT_SEARCHED", "CANCELLED", "OVER_SCOPE_NOT_COUNTED", "UNKNOWN"}
assert states <= ok, states - ok
if res["status"] != "LOCATED":
    assert "INACCESSIBLE" in states or "NOT_SEARCHED" in states, "must not claim global absence"
if res["status"] == "MISSING":
    assert idx["inputs"] == [] and all(v == [] for v in idx["tiers"].values())
    assert idx.get("install_command") is None
for i in idx["inputs"]:
    for k in ("sha256", "size", "package", "versionCode", "signer_cert_sha256", "splitName", "required_for_stage", "source_alias"):
        assert k in i, k
priv = os.path.expanduser("~/.local/share/westlake/commercial-game-20261021/intake")
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
assert refs
checked = 0
for r in refs:
    assert re.fullmatch(r"[0-9a-f]{64}", r["sha256"]) and isinstance(r["size"], int), r
    a = r["alias"]
    assert not a.startswith(("/Users/", "/home/")), "user-bound path " + a
    if a.startswith("$COMMERCIAL_G01_PRIVATE/"):
        if not os.path.isdir(priv):
            continue
        p = os.path.join(priv, a.split("/", 1)[1])
    elif a.startswith("$GENSHIN_T1_PRIVATE/"):
        p = os.path.expanduser("~/.local/share/westlake/genshin-static-intake-20261021/" + a.split("/", 1)[1])
        if not os.path.exists(p):
            continue
    else:
        p = os.path.join(root, a)
    b = open(p, "rb").read()
    assert len(b) == r["size"] and hashlib.sha256(b).hexdigest() == r["sha256"], "ref mismatch " + a
    checked += 1
for c in res["command_receipts"]:
    assert isinstance(c["argv"], list) and c["argv"] and c["raw_refs"] and "rc" in c, c["id"]
    assert c.get("class") and c.get("status_note"), c["id"]
    if c["rc"] is None:
        assert c["class"].startswith("CANCELLED"), c["id"]
    for a in c["argv"]:
        assert "/Users/" not in a and not re.search(r"\b\d+\.\d+\.\d+\.\d+\b", a), "unaliased argv " + c["id"]
summ = json.load(open(os.path.join(d, "local-package-summary.json")))
lay = summ["evidence_layers"]
assert set(lay) == {"apk_android_manifest", "xapk_container_manifest_json"}, lay.keys()
assert "NOT read" in lay["xapk_container_manifest_json"]["boundary"], "xapk boundary must be explicit"
assert sum(v["entries"] for v in lay.values()) == summ["entries"]
ts = res["tool_sources"]
assert {t["alias"].rsplit("/", 1)[1] for t in ts} == {"rec.sh", "pkgnames.py", "gen.py"}
for t in ts:
    assert re.fullmatch(r"[0-9a-f]{64}", t["private_original_sha256"]) and "identical_to_original" in t
    src = open(os.path.join(root, t["alias"])).read()
    assert "/Users/" not in src and not re.search(r"\b\d+\.\d+\.\d+\.\d+\b", src), "unaliased tool " + t["alias"]
print("commercial_game_intake receipt ok: refs", len(refs), "rehashed", checked, "receipts", len(res["command_receipts"]))
"#;

#[test]
fn commercial_game_intake_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("-I")
        .arg("-c")
        .arg(CHECK)
        .arg(&root)
        .status()
        .expect("run COMMERCIAL-G01 receipt check");
    assert!(status.success(), "COMMERCIAL-G01 receipt check failed");
}
