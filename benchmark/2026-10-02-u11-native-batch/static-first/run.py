import hashlib
import json
import os
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
WORKSPACES = Path(os.environ.get("WORKSPACES", REPO.parent))
TOOLS = WORKSPACES / "westlake-harness/scripts/lab"
PAYLOAD = WORKSPACES / "westlake-generation-u9-j10g-238ffc14/native/payload"
ARTIFACTS = HERE.parent / ".artifacts/r1"
RAW = HERE.parent / ".artifacts/static-first/raw"


def sha(filename):
    return hashlib.sha256(filename.read_bytes()).hexdigest()


def portable(value):
    return value.replace(str(REPO) + "/", "$REPO/").replace(str(WORKSPACES), "$WORKSPACES")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    records = {}

    def capture(name, arguments):
        command = [str(value) for value in arguments]
        result = subprocess.run(command, capture_output=True, text=True)
        content = result.stdout + result.stderr
        (RAW / (name + ".txt")).write_text(content)
        display = portable(content)
        (evidence / (name + ".txt")).write_text(display)
        records[name] = {"command": [portable(value) for value in command], "exit_code": result.returncode,
                         "raw_sha256": hashlib.sha256(content.encode()).hexdigest(),
                         "display_sha256": hashlib.sha256(display.encode()).hexdigest()}
        print(name + " exit=" + str(result.returncode), flush=True)

    for name in ["appspawn-x", "libnativeloader.so", "libz.so", "libshared_libz.z.so", "libOpenSLES.so", "libwestlake_android_child.z.so"]:
        capture("whois-" + name, ["python3", TOOLS / "deployed_whois.py", name])

    paths = {
        "host-deployed": PAYLOAD / "runtime/appspawn-x",
        "host-candidate": ARTIFACTS / "host/appspawn-x-candidate",
        "host-r3-reference": REPO / "benchmark/2026-10-01-u10-native-shims/.artifacts/host-r3/appspawn-x-candidate",
        "media-deployed": PAYLOAD / "android/lib64/libnativeloader.so",
        "media-candidate": ARTIFACTS / "media/libnativeloader-candidate.so",
        "zlib-alias": WORKSPACES / "01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so",
        "zlib-provider": PAYLOAD / "android/lib64/libshared_libz.z.so",
        "opensles-facade": PAYLOAD / "android/lib64/libOpenSLES.so",
        "opensles-owner-reference": WORKSPACES / "westlake-inputs/oh-system-libs/opensles-5ea-u9/oh-system-lib64-libOpenSLES.so",
        "child-deployed": PAYLOAD / "runtime/libwestlake_android_child.z.so",
    }
    pinned = {"host-deployed": "1d3b08816969369a1941a3877a8a3d6addf604dd830bd3753bbd883ea74aa8b3",
              "host-candidate": "67753f7700887e4510e215abb2c4791534bb46b46c69e6f4775559c86653d55e",
              "host-r3-reference": "65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284",
              "media-deployed": "fb9dc9372c9d9f1f38f9bc5b218a1a21a3a96ba63c87e2e0bfc0396dd102e159",
              "media-candidate": "7f348fe5bd1751214a9eca21c7ece1d72670a24d08328c389a2496dddd11411b",
              "zlib-alias": "50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d",
              "zlib-provider": "ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc",
              "opensles-facade": "5891f899c2b21dcb24fa2f4cb3db78fbb34597740600c096dd8f633b831c5347",
              "opensles-owner-reference": "05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100"}
    pinned["child-deployed"] = "dc73a28d2535f0a261776625ea51770edf044f33de17aa05ff5c5e789ba25d3c"
    scans = {}
    for name, filename in paths.items():
        actual = sha(filename)
        if name in pinned and actual != pinned[name]:
            raise ValueError(name + " identity changed: " + actual)
        target = RAW / (name + ".json")
        capture(name, ["python3", TOOLS / "open_site_scan.py", filename, "--json", target])
        scans[name] = json.loads(target.read_text())
        (evidence / (name + ".json")).write_text(portable(target.read_text()))
    for name, candidate, deployed in [
        ("host-strings", paths["host-candidate"], paths["host-deployed"]),
        ("media-strings", paths["media-candidate"], paths["media-deployed"]),
        ("zlib-provider-unchanged-strings", paths["zlib-provider"], paths["zlib-provider"]),
        ("opensles-unchanged-strings", paths["opensles-facade"], paths["opensles-facade"]),
        ("opensles-rejected-owner-strings", paths["opensles-owner-reference"], paths["opensles-facade"]),
    ]:
        capture(name, ["python3", TOOLS / "deployed_strings_diff.py", candidate, "--deployed", deployed])
    for name, host in [("deployed-host-child", paths["host-deployed"]), ("candidate-host-child", paths["host-candidate"])]:
        target = RAW / (name + ".json")
        capture(name, ["python3", TOOLS / "open_site_scan.py", host, paths["child-deployed"], "--json", target])
        (evidence / (name + ".json")).write_text(portable(target.read_text()))

    differences = {}
    for family in ["host", "media"]:
        before = scans[family + "-deployed"]["binaries"][0]["sites"]
        after = scans[family + "-candidate"]["binaries"][0]["sites"]
        grouped = []
        for sites in [before, after]:
            ordinal = {}
            indexed = {}
            for site in sites:
                base = (site["function"], site["callee"])
                count = ordinal.get(base, 0)
                ordinal[base] = count + 1
                indexed[base + (count,)] = site
            grouped.append(indexed)
        old, new = grouped
        differences[family] = {
            "before_count": len(before), "after_count": len(after),
            "added": [new[key] for key in sorted(new.keys() - old.keys())],
            "removed": [old[key] for key in sorted(old.keys() - new.keys())],
            "matched": [{"before": old[key], "after": new[key],
                         "changed_fields": [field for field in ["namespace", "path", "flags", "tail_call"] if old[key][field] != new[key][field]]}
                        for key in sorted(old.keys() & new.keys())],
            "match_rule": "function/callee/ordinal; PC and stack offsets are not namespace identities"}
    receipt = {"mode": "offline-static-only", "device_io": False, "package_modified": False,
               "deployed_identity_authority": "U9 signed generation and maps; outer10:50/11:01 and cc-wiki10:09 board baseline, no live device query",
               "inputs": {name: {"path": portable(str(filename)), "sha256": sha(filename)} for name, filename in paths.items()},
               "tools": {name: sha(TOOLS / name) for name in ["open_site_scan.py", "deployed_strings_diff.py", "deployed_whois.py"]},
               "differences": differences, "commands": records,
               "not_run": {"libz_alias_strings": "No deployed libz.so; absent baseline is not PASS",
                           "opensles_candidate": "No admitted replacement; owner comparison is rejected negative control only",
                           "jar_frozen_diff": "No JAR modifications in this native handoff",
                           "Bitmap_ColorSpace": "provenance-blocked, no candidate", "libjnigraphics": "held, no candidate"}}
    (HERE / "results.json").write_text(portable(json.dumps(receipt, indent=2)) + "\n")


if __name__ == "__main__":
    main()
