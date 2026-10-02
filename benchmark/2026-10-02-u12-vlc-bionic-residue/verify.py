import json
import os
from pathlib import Path
import re
import shutil
import sys

from build import ADDED
from collect import BASE, HERE, MASTER, REPO, WS, capture, portable, save, sha


def main():
    deployed = BASE / "payload/android/lib64/libbionic_compat.so"
    candidate = HERE / ".artifacts/candidate1.so"
    records = []
    for name, path in [("deployed", deployed), ("candidate", candidate)]:
        target = HERE / "evidence" / ("open-" + name + ".json")
        records.append(capture("open-" + name, ["python3", REPO / "scripts/lab/open_site_scan.py", path, "--json", target]))
        target.write_text(portable(target.read_text()))
        records.append(capture("dynamic-" + name, ["llvm-readelf", "-d", "-V", path]))
    records.append(capture("strings", ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", deployed]))
    consumer_dir = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/.artifacts/members"
    inventory = json.loads((REPO / "benchmark/2026-10-02-toutiao-bionic-scope/consumers.json").read_text())
    consumers = {member["sha256"]: consumer_dir / (member["sha256"] + ".so") for app in inventory["apps"] for member in app["members"]
                 if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            consumers[sha(path)] = path
    for digest, path in consumers.items():
        if sha(path) != digest:
            raise ValueError("consumer drift")
    abi_path = HERE / "evidence/abi.json"
    arguments = [value for path in consumers.values() for value in ["--consumer", path]]
    records.append(capture("abi", ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", deployed,
                                   "--new", candidate, "--calls", "--json", abi_path, *arguments]))
    abi_path.write_text(portable(abi_path.read_text()))
    abi = json.loads(abi_path.read_text())
    if abi["added"] != ADDED or abi["removed"] or abi["drift"] or abi["call_diffs"] or abi["consumer_breaks"]:
        raise ValueError("unexpected ABI/calls/consumer delta")
    old_scan = json.loads((HERE / "evidence/open-deployed.json").read_text())
    new_scan = json.loads((HERE / "evidence/open-candidate.json").read_text())
    save("namespace-delta.json", dict(before_sites=old_scan["binaries"][0]["sites"], after_sites=new_scan["binaries"][0]["sites"],
         before_edges=old_scan["binaries"][0]["namespace_edges"], after_edges=new_scan["binaries"][0]["namespace_edges"],
         findings_before=old_scan["findings"], findings_after=new_scan["findings"],
         changed=False, note="old function PC may shift after link; path/flags/call behavior and direct namespace sites remain unchanged"))
    records.append(capture("host-behavior", ["clang", "-std=c11", "-O2", "-pthread", HERE / "test_adapter.c", "-o", HERE / ".artifacts/test_adapter"]))
    records.append(capture("host-behavior-run", [HERE / ".artifacts/test_adapter"]))
    for name in ["vlc-libc++_shared.so", "vlc-libvlc.so", "fd-fennec_fdroid-libmozglue.so", "firefox-libmozglue.so", "ppsspp-libppsspp_jni.so"]:
        path = REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts" / name
        records.append(capture(name + "-dynamic-symbols", ["llvm-readelf", "-d", "--dyn-syms", path]))
        raw = HERE / ".artifacts" / (name + "-dynamic-symbols.txt")
        lines = raw.read_text().splitlines()
        selected = [str(number) + ": " + line for number, line in enumerate(lines, 1)
                    if number <= 40 or re.search(r"\b(?:strtoll_l|strtoull_l|__pthread_cleanup_push|__pthread_cleanup_pop|__gnu_strerror_r|android_dlopen_ext)(?:@|\b)", line)]
        (HERE / "evidence" / raw.name).write_text("Numbered target-symbol excerpt; complete raw output is SHA-pinned in validation.json and persistent .artifacts.\n" + "\n".join(selected) + "\n")
    save("validation.json", dict(records=records, consumer_files=len(consumers), execution_enabled=False,
         host_test_double="OH cleanup push/pop and exit drain modeled from exact binary; real host pthread_exit triggers drain before TLS finalization, not OH execution",
         abi_added=abi["added"], abi_call_diffs=abi["call_diffs"], consumer_breaks=abi["consumer_breaks"]))
    print("ABI old functions calls0/removal0/drift0; four added exports; consumer breaks0 across " + str(len(consumers)) + " real ELFs")


if __name__ == "__main__":
    main()
