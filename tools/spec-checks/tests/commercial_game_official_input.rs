use std::path::Path;
use std::process::Command;

// Receipt check for COMMERCIAL-G03: README/results/input-index/source-chain exist; runtime NOT_TESTED;
// LOCATED inputs carry SHA/size/final URL/manifest/signer fields; tiers keep install-set, startup-assets and
// full-content separate (full-content never claimed acquired); no install command; receipts carry argv/rc/
// raw_refs with failures kept; public files hold no user-bound paths. Repo refs are re-hashed; private refs
// and the private APK identity (SHA-256 + size) are re-checked only when the private dir exists.
// Evidence quality stays human-reviewed (pending_review).
const CHECK: &str = r#"
import hashlib, json, os, re, sys
root = sys.argv[1]
d = os.path.join(root, "benchmark/2026-10-21-commercial-game/official-input")
names = ["README.md", "results.json", "input-index.json", "source-chain.json"]
for n in names:
    assert os.path.isfile(os.path.join(d, n)), "missing " + n
J = {n: json.load(open(os.path.join(d, n))) for n in names[1:]}
res, idx, ch = J["results.json"], J["input-index.json"], J["source-chain.json"]
assert res["token"] == idx["token"] == ch["token"] == "COMMERCIAL-G03"
assert res["status"] in ("LOCATED", "PARTIAL", "NOT_OBTAINED") and res["status"] == idx["status"]
assert res["runtime_verdict"] == "NOT_TESTED" and idx["runtime_verdict"] == "NOT_TESTED"
assert idx.get("install_command") is None
for k in ("elapsed", "limits", "unknowns", "next_action", "download_budget", "tool_sources", "command_receipts"):
    assert res.get(k), "results missing " + k
assert set(idx["tiers"]) == {"install-set", "startup-assets", "full-content"}
assert idx["tiers"]["full-content"]["state"] in ("NOT_ACQUIRED", "UNKNOWN"), "full-content must not be claimed"
steps = ch["steps"]
assert [s["step"] for s in steps] == [1, 2, 3, 4, 5]
for s in steps[:4]:
    assert s["evidence"] and all(e["found"] for e in s["evidence"]), "chain step not evidenced %d" % s["step"]
priv = os.path.expanduser("~/.local/share/westlake/commercial-game-20261021/official-input")
total = 0
for i in idx["inputs"]:
    for k in ("sha256", "size", "package", "versionCode", "minSdk", "targetSdk", "abi", "signer", "splitName", "uses_split", "required_for_stage", "source_alias", "private_alias"):
        assert k in i, k
    assert re.fullmatch(r"[0-9a-f]{64}", i["sha256"]) and re.fullmatch(r"[0-9a-f]{64}", i["signer"]["signer_cert_sha256"])
    assert i["http"]["final_url"] == steps[4]["location"], "final URL must equal the official 302 Location"
    assert i["http"]["final_url"].startswith("https://") and str(i["size"]) == i["http"]["content_length"]
    assert i["zip"]["unzip_test_rc"] == 0 and i["signer"]["verifies"]
    total += i["size"]
    apk = os.path.join(priv, i["private_alias"].split("/", 1)[1])
    if os.path.isdir(priv):
        h = hashlib.sha256()
        with open(apk, "rb") as f:
            for blk in iter(lambda: f.read(1 << 22), b""):
                h.update(blk)
        assert os.path.getsize(apk) == i["size"] and h.hexdigest() == i["sha256"], "local APK identity mismatch"
assert total <= res["download_budget"]["limit_bytes"]
def walk(o):
    if isinstance(o, dict):
        if "alias" in o and "sha256" in o and "size" in o:
            yield o
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
refs = [r for n in J for r in walk(J[n])]
checked = 0
for r in refs:
    a = r["alias"]
    assert not a.startswith(("/Users/", "/home/")), "user-bound path " + a
    if a.startswith("$COMMERCIAL_G03_PRIVATE/"):
        if not os.path.isdir(priv) or a.endswith(".apk"):
            continue
        p = os.path.join(priv, a.split("/", 1)[1])
    else:
        p = os.path.join(root, a)
    b = open(p, "rb").read()
    assert len(b) == r["size"] and hashlib.sha256(b).hexdigest() == r["sha256"], "ref mismatch " + a
    checked += 1
for c in res["command_receipts"]:
    assert c["argv"] and c["raw_refs"] and "rc" in c and c["class"] and c["status_note"], c["id"]
    assert (c["rc"] != 0) == (c["class"] == "FAILED_KEPT"), c["id"]
    assert all("/Users/" not in a for a in c["argv"]), "unaliased argv " + c["id"]
for n in names:
    assert "/Users/" not in open(os.path.join(d, n)).read(), "user path in " + n
print("commercial_game_official_input receipt ok: inputs", len(idx["inputs"]), "refs", len(refs), "rehashed", checked, "receipts", len(res["command_receipts"]))
"#;

#[test]
fn commercial_game_official_input_receipt() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
    let status = Command::new("python3")
        .arg("-I")
        .arg("-c")
        .arg(CHECK)
        .arg(&root)
        .status()
        .expect("run COMMERCIAL-G03 receipt check");
    assert!(status.success(), "COMMERCIAL-G03 receipt check failed");
}
