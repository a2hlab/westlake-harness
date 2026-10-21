# Hash given local ELF candidates; for any matching a deployed SHA, report byte offsets of the log literals and DT_NEEDED.
import hashlib, json, subprocess, sys
want = {"51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5": "libinstalls.z.so",
        "c39eba26367bcbcc40a5d230297f85ac8888004c632eb7eaca84023cd9cab6aa": "libappexecfwk_common.z.so",
        "85c84aff96b10e5ba2f3f5138bdb5b864c321f1fa00d5153f7143b363e5b869d": "libappexecfwk_base.z.so",
        "13e03d9c2c1bc591804af3db6dc20848f85a738d42c190e347c062f8ad830ba0": "libextractortool.z.so",
        "7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18": "libapk_installer.so"}
lits = [b"endDir.numDisk", b"open zip file failed", b"APK extractor init failed", b"CheckEndDir", b"ExtractApkNativeFiles"]
for p in sys.argv[1:]:
    try: b = open(p, "rb").read()
    except OSError as e: print(json.dumps({"path": p, "error": str(e)})); continue
    h = hashlib.sha256(b).hexdigest()
    row = {"path": p, "sha256": h, "deployed_match": want.get(h)}
    if h in want:
        row["literals"] = {l.decode(): b.find(l) for l in lits}
        r = subprocess.run(["llvm-readelf", "-d", p], capture_output=True, text=True)
        row["needed"] = [x.split("[")[1].rstrip("]") for x in r.stdout.splitlines() if "(NEEDED)" in x]
    print(json.dumps(row))
