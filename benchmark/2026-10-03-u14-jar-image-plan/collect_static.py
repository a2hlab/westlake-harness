import json
from pathlib import Path
import subprocess
import sys

from prepare_inputs import BASE, HERE, HOST, MASTER, PRIVATE, RUNTIME, STUBS, WS, portable, save, sha


def capture(name, command):
    raw = HERE / ".artifacts/raw" / (name + ".txt")
    raw.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.run([str(item) for item in command], capture_output=True, text=True,
        errors="replace", timeout=300)
    raw.write_text(process.stdout + process.stderr)
    evidence = HERE / "evidence" / (name + ".txt")
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(portable(raw.read_text()))
    print(name + " exit=" + str(process.returncode), flush=True)
    return dict(command=portable(command), exit_code=process.returncode, raw=portable(raw),
        raw_sha256=sha(raw), evidence=portable(evidence), evidence_sha256=sha(evidence))


def main():
    tools = MASTER / "scripts/lab"
    host = PRIVATE / "native-slots/appspawn-x"
    old_host = BASE / "native/payload/runtime/appspawn-x"
    if sha(host) != HOST:
        raise ValueError("Staged host changed")
    results = []
    t8 = WS / "westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3"
    results.append(capture("host-whois-t8-inventory", [sys.executable, tools / "deployed_whois.py", "appspawn-x", "--generation", t8]))
    for name, source in [("host-open-u13", old_host), ("host-open-u14", host)]:
        destination = HERE / ".artifacts/raw" / (name + ".json")
        results.append(capture(name, [sys.executable, tools / "open_site_scan.py", source, "--json", destination]))
        save("evidence/" + name + ".json", json.loads(destination.read_text()))
    results.append(capture("host-strings-vs-u13", [sys.executable, tools / "deployed_strings_diff.py", host, "--deployed", old_host]))
    native_pairs = [
        ("flutter", PRIVATE / "native-slots/westlake_flutter/libandroid.so", BASE / "native/payload/android/lib64/westlake_flutter/libandroid.so"),
        ("gecko-abi", PRIVATE / "native-slots/westlake_native/libwestlake_native_abi.so", BASE / "native/payload/android/lib64/westlake_native/libwestlake_native_abi.so"),
        ("icu", PRIVATE / "native-slots/libicuuc.so", BASE / "native/payload/android/lib64/libicuuc.so")]
    for name, candidate, deployed in native_pairs:
        results.append(capture(name + "-whois-t8-inventory", [sys.executable, tools / "deployed_whois.py", deployed.name, "--generation", t8]))
        for suffix, source in [("u13", deployed), ("u14", candidate)]:
            destination = HERE / ".artifacts/raw" / (name + "-open-" + suffix + ".json")
            results.append(capture(name + "-open-" + suffix, [sys.executable, tools / "open_site_scan.py", source, "--json", destination]))
            save("evidence/" + name + "-open-" + suffix + ".json", json.loads(destination.read_text()))
        results.append(capture(name + "-strings-vs-u13", [sys.executable, tools / "deployed_strings_diff.py", candidate, "--deployed", deployed]))
    shim = PRIVATE / "native-slots/libicu74compat.so"
    results.append(capture("icu-shim-open-u14", [sys.executable, tools / "open_site_scan.py", shim]))
    runtime = PRIVATE / "runtime/oh-adapter-runtime.jar"
    stubs = PRIVATE / "jars9/adapter-mainline-stubs.jar"
    if sha(runtime) != RUNTIME or sha(stubs) != STUBS:
        raise ValueError("Staged JAR changed")
    bundle = json.loads((BASE / "bundle.json").read_text())
    old_runtime = BASE / bundle["runtime_jar"]["source"]
    old_stubs = next(BASE / row["source"] for row in bundle["boot_group"]["members"]
        if row["target"].endswith("/adapter-mainline-stubs.jar"))
    for name, candidate, deployed in [("runtime-class-vs-u13", runtime, old_runtime), ("stubs-class-vs-u13", stubs, old_stubs)]:
        results.append(capture(name, [sys.executable, tools / "deployed_class_diff.py", candidate,
            "--deployed", deployed, "--frozen"]))
    save("static-input-checks.json", dict(scope="read-only donor input checks, no composed U14 gates or authorization",
        results=results, host_baseline=dict(path=old_host, sha256=sha(old_host)),
        deployment_limitation="whois inventory is the signed T8 generation; ongoing U13 window is not a promotion receipt",
        native_gate_status="PENDING final assembly", bake_status="NOT_RUN",
        new_library=dict(path=shim, sha256=sha(shim), deployed_counterpart=None,
            strings_comparison="not applicable: new soname; do not fabricate an empty ELF baseline; admission required")))


if __name__ == "__main__":
    main()
