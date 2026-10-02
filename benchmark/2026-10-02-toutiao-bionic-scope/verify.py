import difflib
import json
from pathlib import Path

from audit import COMPAT, HERE, HOST, LOADER, MASTER, WS, elf, portable, run, save, sha


def main():
    records, variants = [], {}
    inventory = json.loads((HERE / "consumers.json").read_text())
    consumer_shas = sorted({member["sha256"] for app in inventory["apps"] for member in app["members"]
                            if member["status"] == "ELF64-AArch64" and member["imports"]})
    for name, candidate, deployed in [
        ("exports-only", HERE / ".artifacts/build/exports-only.so", COMPAT),
        ("scope-global-reference", HERE / ".artifacts/build/scope-global-reference.so", COMPAT),
        ("host-proposal", HERE / ".artifacts/host/resident-global-proposal/appspawn-x", HOST),
    ]:
        records.append(run("open-" + name, ["python3", MASTER / "scripts/lab/open_site_scan.py", candidate,
                          "--json", HERE / ".artifacts" / ("open-" + name + ".json")]))
        save("evidence/open-" + name + ".json", json.loads((HERE / ".artifacts" / ("open-" + name + ".json")).read_text()))
        records.append(run("strings-" + name, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate,
                                              "--deployed", deployed]))
        consumers = [HERE / ".artifacts/members" / (digest + ".so") for digest in consumer_shas] if name != "host-proposal" else [LOADER]
        consumer_args = [value for consumer in consumers for value in ["--consumer", consumer]]
        records.append(run("abi-" + name, ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", deployed,
                     "--new", candidate, "--calls", *consumer_args,
                     "--json", HERE / ".artifacts" / ("abi-" + name + ".json")]))
        save("evidence/abi-" + name + ".json", json.loads((HERE / ".artifacts" / ("abi-" + name + ".json")).read_text()))
        records.append(run("dynamic-" + name, ["llvm-readelf", "-d", candidate]))
        records.append(run("versions-" + name, ["llvm-readelf", "-V", candidate]))
        variants[name] = dict(path=portable(candidate), sha256=sha(candidate), elf=elf(candidate.read_bytes()))
    current_libc = WS / "westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1"
    if sha(current_libc) != "fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2":
        raise ValueError("OH frozen libc reference drift")
    records.append(run("oh-libc-decode-dyn", ["llvm-objdump", "-d", "--no-show-raw-insn", "--start-address=0x80b78",
                                               "--stop-address=0x80e24", current_libc]))
    for name, start, stop in [
        ("oh-libc-saved-scope", "0x80e24", "0x81024"),
        ("oh-libc-relocation-version", "0x8cf78", "0x8d134"),
        ("oh-libc-check-version", "0x8b20c", "0x8b34c"),
        ("oh-libc-provider-check", "0x8d8ec", "0x8d958"),
        ("oh-libc-retain-chain", "0x866a4", "0x86810"),
    ]:
        records.append(run(name, ["llvm-objdump", "-d", "--no-show-raw-insn",
                                 "--start-address=" + start, "--stop-address=" + stop, current_libc]))
    old_host = json.loads((HERE / "evidence/open-host-r3.json").read_text())["binaries"][0]
    new_host = json.loads((HERE / "evidence/open-host-proposal.json").read_text())["binaries"][0]
    site_delta = []
    for old, new in zip(old_host["sites"], new_host["sites"]):
        if old != new:
            site_delta.append(dict(old=old, new=new))
    save("evidence/namespace-delta.json", dict(old_sites=len(old_host["sites"]), new_sites=len(new_host["sites"]),
         changed=site_delta, old_edges=old_host["namespace_edges"], new_edges=new_host["namespace_edges"],
         findings_old=old_host["findings"] if "findings" in old_host else json.loads((HERE / "evidence/open-host-r3.json").read_text())["findings"],
         findings_new=new_host["findings"] if "findings" in new_host else json.loads((HERE / "evidence/open-host-proposal.json").read_text())["findings"]))
    source = HERE / "resident-compat-proposal.h"
    old_source = HERE.parents[1] / "benchmark/2026-10-02-n11h-host-owner/inputs/resident-compat.h"
    (HERE / "evidence/host-promotion.patch").write_text("".join(difflib.unified_diff(old_source.read_text().splitlines(True),
         source.read_text().splitlines(True), fromfile="r3/resident-compat.h", tofile="proposal/resident-compat.h")))
    save("candidate-evidence.json", dict(device_io=False, variants=variants, tool_records=records,
         current_oh_libc_reference=dict(path=portable(current_libc), sha256=sha(current_libc),
         decode_dyn_entry="0x80b78", df1_global_test="0x80c50 bit1", global_store="0x80c88 dso+0x230",
         correction="0x88040 is prepare_lazy NOW filtering, not decode_dyn; its absence of GLOBAL is not a loader drift proof"),
         recommended_proposal=["scope-global-reference", "host-proposal"],
         publication_status="OFFLINE_STATIC_ONLY_PENDING_ACTUAL_RELOCATION_AND_OWNER_ORACLE",
         version_node_change=False,
         explanation="Pinned fd3c relocation8d0e4 fills the requested hash; provider check8b294 accepts absent version tables when the name string is empty. DF1_GLOBAL80c88 and saved-scope80f58 match the relevant reference behavior, not source provenance. Named LIBC is not shown necessary for these ordinary relocations; actual owner binding remains unverified.",
         prohibited=["application-view NOLOAD", "default fresh fallback", "app APK rewrites", "second same-parent inherit", "second compat owner"],
         caveat="Binary80f58 filters non-global providers; 867e4 tests RTLD_GLOBAL and otherwise clears syms_next. Pairing flags addresses these static conditions, but owner residency, query timing and actual relocation success require a future oracle. Global promotion widens binding for all old exports and is not approved."))
    print("static candidates: exact015a/65cc baselines reproduced; exported errno+cmsg; no version node changed")
    for name, variant in variants.items():
        print(name + " " + variant["sha256"] + " FLAGS1=" + str(variant["elf"].get("flags1")))
    for record in records:
        if record["label"].startswith(("abi-", "strings-")):
            print(record["label"] + " exit=" + str(record["exit_code"]))


if __name__ == "__main__":
    main()
