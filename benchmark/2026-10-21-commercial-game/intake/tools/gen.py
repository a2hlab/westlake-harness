# Generate COMMERCIAL-G01 intake outputs from captured receipts (no device, no package execution).
import collections, hashlib, json, os, re, sys
P = os.environ.get("COMMERCIAL_G01_PRIVATE") or os.path.expanduser("~/.local/share/westlake/commercial-game-20261021/intake")
OUT = sys.argv[1]; T0 = int(sys.argv[2]); T1 = int(sys.argv[3])
RAW = os.path.join(P, "raw")
def ref(name):
    b = open(os.path.join(RAW, name), "rb").read()
    return {"alias": "$COMMERCIAL_G01_PRIVATE/raw/" + name, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b)}
def rd(name, default=None):
    p = os.path.join(RAW, name)
    return open(p).read().strip() if os.path.exists(p) else default
NOTES = {
 "c01-local-manifest-pkgnames": ("COVERAGE", "441 reused s08 entries, two evidence layers: 393 .apk via aapt2 dump badging of the APK's own binary AndroidManifest.xml; 48 .xapk via the container manifest.json (packer metadata, NOT the embedded base APK manifest, which was not read); 0 parse failures"),
 "r01-orb-a2hlab-find-names": ("OVER_SCOPE_KEPT", "non-root rootfs -xdev name find; completed rc0 with only permission-denied lines; exceeds contract (no whole-disk) so NOT counted as authorized coverage"),
 "r02-hw248-find-names": ("CANCELLED_OVER_SCOPE", "whole-disk name find stopped on outer correction 14:28 (TaskStop+pkill); rc unknown; partial 4096 B stdout = repo/evidence script & screenshot names only, no package file; not coverage"),
 "r03-macserver-doc-mdfind-find": ("INACCESSIBLE", "documented macserver route, existing ssh config BatchMode: connection closed by remote (rc 255) before any command"),
 "r04-mac-server-128-mdfind-find": ("INACCESSIBLE", "ssh alias mac-server-128, BatchMode: connection closed by remote (rc 255)"),
 "r05-orb-a2hlab-mounts": ("CONTEXT", "a2hlab mounts: btrfs root, /mnt/mac = this Mac (virtiofs), /mnt/machines/oh7x86"),
 "r06-orb-a2hlab-root-find-names": ("CANCELLED_OVER_SCOPE", "root whole-disk find opened by cc-video, stopped on outer correction 14:28; rc unknown, 0 B; not coverage"),
 "r07-orb-a2hlab-inputs-names": ("COVERAGE", "env.md input root ~/a2hlab/ws/inputs maxdepth 6: only toolchain dirs, no apk/xapk/apks/obb or name match"),
 "r08-hw248-state-roots-ls": ("CONTEXT", "ls of hw248 /home/alvin top dirs; rc 2 only because linux_cache root /opt/build-trees/bridge-demo-artifact-cache is absent"),
 "r09-hw248-artifact-roots-names": ("COVERAGE", "hw248 documented artifact/input roots (westlake-artifacts, *-inputs, boat-v2-inputs, final61b-game) maxdepth 6: 0 apk/xapk/apks/obb, 0 name match"),
}
HOME = os.path.expanduser("~")
def alias_args(argv):
    out = []
    for i, a in enumerate(argv):
        out.append("<port>" if i > 0 and argv[i - 1] == "-p" else alias_arg(a))
    return out
def alias_arg(a):
    a = a.replace(HOME, "$HOME")
    a = re.sub(r"[A-Za-z0-9_.-]+@\d+\.\d+\.\d+\.\d+", "<macserver-doc>", a)
    a = re.sub(r"\b\d+\.\d+\.\d+\.\d+\b", "<host>", a)
    return a
receipts = []
for rid, (cls, note) in NOTES.items():
    refs = [ref(rid + ext) for ext in (".argv.json", ".stdout", ".stderr") if os.path.exists(os.path.join(RAW, rid + ext))]
    for ext in (".rc", ".cancel.json"):
        if os.path.exists(os.path.join(RAW, rid + ext)): refs.append(ref(rid + ext))
    rc = rd(rid + ".rc"); rc = int(rc) if rc is not None else None
    receipts.append({"id": rid, "argv": alias_args(json.load(open(os.path.join(RAW, rid + ".argv.json")))),
                     "argv_note": "public argv aliased ($HOME, host aliases); exact argv in raw_refs[0]", "rc": rc,
                     "class": cls, "status_note": note, "raw_refs": refs})
# package summary from c01
rows = [json.loads(l) for l in open(os.path.join(RAW, "c01-local-manifest-pkgnames.stdout"))]
pk = collections.Counter()
for r in rows:
    name = r.get("package") or (re.search(r"name='([^']+)'", r.get("package_line") or "") or [None, None])[1]
    pk[name] += 1
unknown = sum(1 for r in rows if "error" in r or (r.get("kind") == "apk" and not r.get("package_line")))
mihoyo = sorted(p for p in pk if p and re.search(r"mihoyo|genshin|yuanshen|hoyo", p, re.I))
layers = {"apk_android_manifest": collections.Counter(), "xapk_container_manifest_json": collections.Counter()}
for r in rows:
    name = r.get("package") or (re.search(r"name='([^']+)'", r.get("package_line") or "") or [None, None])[1]
    layers["apk_android_manifest" if r.get("kind") == "apk" else "xapk_container_manifest_json"][name] += 1
summary = {"evidence_layers": {
             "apk_android_manifest": {"entries": sum(layers["apk_android_manifest"].values()), "distinct_packages": len(layers["apk_android_manifest"]),
                                      "tool": "aapt2 dump badging (build-tools 37.0.0)", "reads": "APK binary AndroidManifest.xml"},
             "xapk_container_manifest_json": {"entries": sum(layers["xapk_container_manifest_json"].values()), "distinct_packages": len(layers["xapk_container_manifest_json"]),
                                              "tool": "zipfile read of manifest.json", "reads": "XAPK packer metadata only",
                                              "boundary": "embedded base/split APK AndroidManifest.xml NOT read; package identity is the container claim, unverified"}},
           "known_tool_defect": "pkgnames.py 'split' field is always null (aapt2 reports split= inside the package: line, which is kept verbatim in package_line)",
           "entries": len(rows), "apk": sum(1 for r in rows if r.get("kind") == "apk"),
           "xapk": sum(1 for r in rows if r.get("kind") == "xapk"), "manifest_unknown": unknown,
           "distinct_packages": len(pk), "mihoyo_like_packages": mihoyo, "packages": dict(sorted(pk.items(), key=lambda x: str(x[0])))}
json.dump(summary, open(os.path.join(OUT, "local-package-summary.json"), "w"), indent=1, ensure_ascii=False)
sb = open(os.path.join(OUT, "local-package-summary.json"), "rb").read()
summary_ref = {"alias": "benchmark/2026-10-21-commercial-game/intake/local-package-summary.json",
               "sha256": hashlib.sha256(sb).hexdigest(), "size": len(sb)}
prior = os.path.expanduser("~/.local/share/westlake/genshin-static-intake-20261021/raw/s08-apk-obb-inventory.stdout")
pb = open(prior, "rb").read()
sources = [
 {"source": "local-mac/apk-stores (westlake-inputs/apks, 00.Workspace/APKS, vm-copies/apks-77, demo-baseline originals)", "state": "MISSING",
  "method": "manifest package read of reused GENSHIN-T1 s08 list", "receipts": ["c01-local-manifest-pkgnames"],
  "reused_list": {"alias": "$GENSHIN_T1_PRIVATE/raw/s08-apk-obb-inventory.stdout", "sha256": hashlib.sha256(pb).hexdigest(), "size": len(pb)},
  "result": f"{len(rows)} entries, {len(pk)} distinct packages, manifest UNKNOWN {unknown}, miHoYo-like {mihoyo}"},
 {"source": "local-mac/westlake-inputs, 00.Workspace, vm-copies names+text indexes", "state": "MISSING", "method": "reused GENSHIN-T1 s03/s04/s07 (not rerun)", "receipts": ["GENSHIN-T1:s03,s04,s07"]},
 {"source": "orbstack-a2hlab:~/a2hlab/ws/inputs", "state": "MISSING", "receipts": ["r07-orb-a2hlab-inputs-names"]},
 {"source": "orbstack-a2hlab:rootfs (non-root -xdev)", "state": "OVER_SCOPE_NOT_COUNTED", "receipts": ["r01-orb-a2hlab-find-names"]},
 {"source": "orbstack-a2hlab:rootfs (root)", "state": "CANCELLED", "receipts": ["r06-orb-a2hlab-root-find-names"]},
 {"source": "hw248:/home/alvin documented artifact & input roots", "state": "MISSING", "receipts": ["r08-hw248-state-roots-ls", "r09-hw248-artifact-roots-names"]},
 {"source": "hw248:LAB_STATE_DIR mirror", "state": "NOT_SEARCHED", "why": "env.md says the directory name is given by the operator; not identified in this slice"},
 {"source": "hw248:linux_cache /opt/build-trees/bridge-demo-artifact-cache", "state": "MISSING_ROOT", "receipts": ["r08-hw248-state-roots-ls"]},
 {"source": "hw248:whole disk", "state": "CANCELLED", "receipts": ["r02-hw248-find-names"]},
 {"source": "macserver (documented route, emulator+Genshin per infra/access.md)", "state": "INACCESSIBLE", "receipts": ["r03-macserver-doc-mdfind-find"]},
 {"source": "macserver primary artifact store (demo-artifact-cache.json primary root)", "state": "INACCESSIBLE", "why": "same host as r03, ssh refused"},
 {"source": "mac-server-128 alias", "state": "INACCESSIBLE", "receipts": ["r04-mac-server-128-mdfind-find"]},
 {"source": "macserver Android emulator userdata (installed Genshin)", "state": "INACCESSIBLE", "why": "host unreachable; extracting an installed package would also require ADB, prohibited by this card"},
 {"source": "rest of local $HOME, a2hlab /mnt/mac, other ssh hosts", "state": "NOT_SEARCHED"},
]
elapsed = T1 - T0
TOOLS = os.path.dirname(os.path.abspath(__file__))
ORIG = {"rec.sh": "05ce4640b83cb361a0d949f621376ab4a6affdcd3648784e6e4121a156c9fed9",
        "pkgnames.py": "d8e70583d376d78a1ec095e7a982908a517877cbd19b150ecb07701c8ef7b193",
        "gen.py": "5a23a9a00184bd87efeae42d1d3c41de85e28d0d946ab9bf5456a6fb92dee31f"}
def tool_sources():
    out = []
    for n, o in ORIG.items():
        b = open(os.path.join(TOOLS, n), "rb").read()
        out.append({"alias": "benchmark/2026-10-21-commercial-game/intake/tools/" + n, "sha256": hashlib.sha256(b).hexdigest(), "size": len(b),
                    "private_original_sha256": o, "identical_to_original": hashlib.sha256(b).hexdigest() == o})
    return out
na = ("Outer loop selects an official acquisition source for the com.miHoYo.Yuanshen install set (base + every split, plus OBB/startup assets if any) "
      "into a private dir; repairing the macserver route is NOT a prerequisite. Then rerun G01 manifest/signer/split reads on the exact SHAs. "
      "Optional bounded follow-ups (OrbStack/hw248 already covered for documented roots): hw248 LAB_STATE_DIR mirror if its name is supplied; "
      "embedded base manifests of the 48 XAPK containers if the reviewer wants that layer closed. No device task.")
res = {"token": "COMMERCIAL-G01", "status": "MISSING", "runtime_verdict": "NOT_TESTED",
       "contract": "specs/commercial-game-round1/t1-input-discovery.spec.md @ 8189ec8d7 (dispatched fb08522d6)",
       "scope": sources, "elapsed": {"start_epoch": T0, "end_epoch": T1, "seconds": elapsed, "budget_seconds": 900},
       "limits": ["no device ops (HDC/ADB 0)", "no download/install/login/package execution/REA", "name searches only, no binary content grep",
                  "two whole-disk finds (r02 hw248, r06 a2hlab root) were opened then cancelled on outer correction; r01 non-root rootfs find completed but is over-scope and not counted",
                  "48 XAPK entries: identity from container manifest.json only; embedded base APK manifests not read (a mislabelled container is not excluded)"],
       "unknowns": ["whether macserver primary store holds a Genshin APK set (INACCESSIBLE)", "hw248 LAB_STATE_DIR mirror contents (NOT_SEARCHED)",
                    "Genshin package/versionCode/signature/splits/ABI/SDK all UNKNOWN (no input)",
                    "embedded base APK package of each of the 48 XAPK containers (not read)"],
       "install_tiers": {"install-set": "MISSING", "startup-assets": "UNKNOWN", "full-content": "UNKNOWN"},
       "tool_sources": tool_sources(),
       "next_action": na, "local_package_summary": summary_ref, "command_receipts": receipts}
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, ensure_ascii=False)
json.dump({"token": "COMMERCIAL-G01", "status": "MISSING", "runtime_verdict": "NOT_TESTED", "inputs": [],
           "tiers": {"install-set": [], "startup-assets": [], "full-content": []},
           "target_packages": ["com.miHoYo.Yuanshen (preferred)", "com.miHoYo.GenshinImpact"],
           "per_package_fields_when_found": ["sha256", "size", "package", "versionCode", "minSdk", "targetSdk", "abi", "signer_cert_sha256",
                                             "splitName", "uses-split", "required_for_stage", "source_alias"],
           "install_command": None}, open(os.path.join(OUT, "input-index.json"), "w"), indent=1, ensure_ascii=False)
json.dump({"token": "COMMERCIAL-G01", "sources": sources}, open(os.path.join(OUT, "source-index.json"), "w"), indent=1, ensure_ascii=False)
print("gen ok", elapsed, "s", len(receipts), "receipts")
