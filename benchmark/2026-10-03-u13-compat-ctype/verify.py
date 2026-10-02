import json
from pathlib import Path
import re
import struct
import subprocess

from common import DEPLOYED, HERE, MASTER, OLD, PRIOR, REPO, WS, capture, expand, portable, save, sha


def defined(path):
    text = subprocess.check_output(["llvm-nm", "-D", "--defined-only", "--format=just-symbols", path], text=True)
    return {name.split("@")[0] for name in text.splitlines()}


def read_va(path, address, size):
    data = Path(path).read_bytes()
    offset = struct.unpack_from("<Q", data, 32)[0]
    entry_size, count = struct.unpack_from("<HH", data, 54)
    for index in range(count):
        kind, _, file_offset, virtual, _, file_size, _, _ = struct.unpack_from("<IIQQQQQQ", data, offset + index * entry_size)
        if kind == 1 and virtual <= address and address + size <= virtual + file_size:
            return data[file_offset + address - virtual:file_offset + address - virtual + size]
    raise ValueError("address is outside file-backed load segment")


def main():
    candidate = HERE / ".artifacts/candidate1.so"
    baseline = HERE / ".artifacts/baseline1.so"
    deployed = WS / "westlake-inputs/generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle/native/payload/android/lib64/libbionic_compat.so"
    if sha(baseline) != OLD or sha(deployed) != DEPLOYED:
        raise ValueError("comparison identity changed")
    records = [capture("whois-compat", ["python3", MASTER / "scripts/lab/deployed_whois.py", "libbionic_compat.so", "--generation", deployed.parents[3]])]
    for label, path in [("b2", baseline), ("candidate", candidate), ("deployed", deployed)]:
        output = HERE / "evidence" / ("open-" + label + ".json")
        records.append(capture("open-" + label, ["python3", MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
        save(output.relative_to(HERE), json.loads(output.read_text()))
        records.append(capture("dynamic-" + label, ["llvm-readelf", "-d", "-V", path]))
    for label, path in [("b2", baseline), ("deployed", deployed)]:
        records.append(capture("strings-" + label, ["python3", MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", path], allowed=(0, 1)))
    inventory_path = REPO / "benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = json.loads(inventory_path.read_text())
    member_root = inventory_path.parent / ".artifacts/members"
    consumers = {member["sha256"]: member_root / (member["sha256"] + ".so")
                 for app in inventory["apps"] for member in app["members"] if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (REPO / "benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            consumers[sha(path)] = path
    if len(consumers) != 219:
        raise ValueError("expected same219 admitted consumer set")
    for digest, path in consumers.items():
        if sha(path) != digest:
            raise ValueError("consumer drift")
    abi_path = HERE / "evidence/abi-b2.json"
    records.append(capture("abi-b2", ["python3", MASTER / "scripts/lab/abi_diff.py", "--old", baseline, "--new", candidate,
        "--calls", "--json", abi_path, *[value for path in consumers.values() for value in ["--consumer", path]]]))
    save(abi_path.relative_to(HERE), json.loads(abi_path.read_text()))
    abi = json.loads(abi_path.read_text())
    if abi["added"] != ["_ctype_"] or any(abi[name] for name in ["removed", "drift", "call_diffs", "consumer_breaks"]):
        raise ValueError("single-export gate failed")
    records.append(capture("symbols-candidate", ["llvm-readelf", "-s", "--wide", candidate]))
    records.append(capture("relocations-candidate", ["llvm-readelf", "-r", "--wide", candidate]))
    symbols = (HERE / ".artifacts/raw/symbols-candidate.txt").read_text()
    pointer = re.search(r"\d+:\s+([0-9a-f]+)\s+8\s+OBJECT\s+GLOBAL\s+DEFAULT\s+\d+\s+_ctype_$", symbols, re.M)
    table = re.search(r"\d+:\s+([0-9a-f]+)\s+257\s+OBJECT\s+LOCAL\s+DEFAULT\s+\d+\s+_C_ctype_$", symbols, re.M)
    if not pointer or not table:
        raise ValueError("wrong pointer/table symbol layout")
    pointer_va, table_va = int(pointer.group(1), 16), int(table.group(1), 16)
    relocations = (HERE / ".artifacts/raw/relocations-candidate.txt").read_text()
    if not re.search(r"^" + f"{pointer_va:016x}" + r"\s+\S+\s+R_AARCH64_RELATIVE\s+" + f"{table_va:x}" + r"$", relocations, re.M):
        raise ValueError("pointer does not relocate to the exact table")
    table_bytes = read_va(candidate, table_va, 257)
    oracle = json.loads((HERE / "table-oracle.json").read_text())
    if list(table_bytes) != oracle["bytes"]:
        raise ValueError("ELF table differs from original")
    save("table-proof.json", dict(candidate_sha256=sha(candidate), pointer=dict(address=hex(pointer_va), size=8,
         binding="GLOBAL", version="unversioned; no new version node", relocation="R_AARCH64_RELATIVE", target=hex(table_va)),
         table=dict(address=hex(table_va), size=257, binding="LOCAL", bytes=list(table_bytes)), matches_original=True,
         consumer=dict(sha256="b7efab7537ed532ecca1dca6fe18878f4f06f3bc78b9fba65a69ed53ba8f1e1c",
         version="_ctype_@LIBC", got="0xb8b3e8", pointer_load_pc="0x7715e8", byte_load_pc="0x7715f4")))
    save("consumer-set.json", dict(count=219, files=[dict(path=path, sha256=digest) for digest, path in sorted(consumers.items())],
         inventory_sha256=sha(inventory_path), abi_json_sha256=sha(abi_path)))
    save("validation.json", dict(records=records, abi_added=["_ctype_"], calls_changed=0, consumer_count=219,
         consumer_breaks=0, table_matches=True, execution_enabled=False))
    print("ABI +1 _ctype_; drift0/removal0/calls0; 219 consumers0 broken; pointer8/table257 exact")


if __name__ == "__main__":
    main()
