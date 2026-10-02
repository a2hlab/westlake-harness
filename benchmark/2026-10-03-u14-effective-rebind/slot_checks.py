import json
from pathlib import Path
import sys

from finalize import HERE, MASTER, PRIOR, WS, save, sha
from reports import capture, expand
from validation import ABI_MEMBER


def consumers():
    inventory_path = WS / "westlake-harness-bms/benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = json.loads(inventory_path.read_text())
    member_root = inventory_path.parent / ".artifacts/members"
    selected = {member["sha256"]: member_root / (member["sha256"] + ".so") for app in inventory["apps"] for member in app["members"] if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (WS / "westlake-harness-bms/benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            selected[sha(path)] = path
    if len(selected) != 219 or any(sha(path) != digest for digest, path in selected.items()):
        raise ValueError("Pinned 219 consumers changed")
    return selected


def main():
    composition = json.loads((HERE / "common/composition.json").read_text())
    package = expand(composition["package"])
    candidate = package / "native" / ABI_MEMBER
    old_versions = {"u14-v1": PRIOR / ".artifacts/bundle/native" / ABI_MEMBER,
        "u13": expand(composition["transaction_base"]) / "native" / ABI_MEMBER}
    selected = consumers()
    save(HERE / "slot-consumers.json", dict(count=len(selected), members=[dict(path=path, sha256=digest) for digest, path in sorted(selected.items())]))
    records = [capture(HERE, "slot-whois", [sys.executable, MASTER / "scripts/lab/deployed_whois.py", "libwestlake_native_abi.so"])]
    scans = {}
    for label, path in dict(old_versions, **{"u14-v2": candidate}).items():
        output = HERE / ".artifacts" / ("open-slot-" + label + ".json")
        records.append(capture(HERE, "open-slot-" + label, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
        scans[label] = json.loads(output.read_text())
        save(HERE / "evidence" / ("open-slot-" + label + ".json"), scans[label])
        records.append(capture(HERE, "dynamic-slot-" + label, ["llvm-readelf", "-d", "--wide", path]))
        records.append(capture(HERE, "dynsym-slot-" + label, ["llvm-readelf", "--dyn-syms", "--wide", path]))
    abi_results = {}
    for label, path in old_versions.items():
        records.append(capture(HERE, "strings-slot-vs-" + label, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", path]))
        output = HERE / ".artifacts" / ("abi-slot-vs-" + label + ".json")
        records.append(capture(HERE, "abi-slot-vs-" + label, [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", path, "--new", candidate,
            "--calls", "--json", output, *[item for consumer in selected.values() for item in ["--consumer", consumer]]]))
        abi_results[label] = json.loads(output.read_text())
        save(HERE / "evidence" / ("abi-slot-vs-" + label + ".json"), abi_results[label])
    save(HERE / "slot-checks.json", dict(candidate_sha256=sha(candidate), consumer_count=len(selected), records=records, abi_results=abi_results,
        deployed_reference=dict(path=old_versions["u13"], sha256=sha(old_versions["u13"]), role="signed-U13-candidate-bytes-not-current-promotion"),
        baseline_v1=dict(path=old_versions["u14-v1"], sha256=sha(old_versions["u14-v1"])),
        prediction=dict(mcdonalds="moves past _ctype_; next unknown", **{"fd-im-vector-app": "moves past _ctype_; next unknown", "fd-meet": "0; deferred U15"}),
        predicted_first_fatal_movement=2, board_verified_movement=0, execution_enabled=False))
    print("Fresh slot open/strings/ABI/calls/219 consumers recorded; predictions are not board evidence")


if __name__ == "__main__":
    main()
