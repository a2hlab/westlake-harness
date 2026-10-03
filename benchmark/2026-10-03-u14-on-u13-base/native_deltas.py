import sys

from common import HERE, LANE, MASTER, capture, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static


def main():
    composition = load(HERE / "common/composition.json")
    package, baseline = expand(composition["package"]), expand(composition["transaction_base"])
    old, current = static.effective(baseline), static.effective(package)
    inventory = load(LANE / "benchmark/2026-10-03-u15-final-assembly/consumer-set.json")
    consumers = [expand(row["source"]) for row in inventory["members"]]
    if len(consumers) != 219 or any(sha(path) != row["sha256"] for path, row in zip(consumers, inventory["members"])):
        raise ValueError("Pinned 219 consumer inventory changed")
    save("consumer-set.json", inventory)
    tools = [MASTER / "scripts/lab" / name for name in ["deployed_strings_diff.py", "abi_diff.py", "open_site_scan.py"]]
    before = {str(path): sha(path) for path in tools}
    records, members, seen = [], [], set()
    for row in composition["increments"]:
        if row["layer"] != "native":
            continue
        candidate = bundle.member(package, current[row["target"]])
        pair = (row["baseline_sha256"], row["candidate_sha256"])
        if pair in seen:
            continue
        seen.add(pair)
        label = "host" if candidate.name == "appspawn-x" else "flutter" if "westlake_flutter" in row["target"] else candidate.name.removeprefix("lib").removesuffix(".so")
        versions = [("candidate", candidate)]
        if row["baseline_sha256"]:
            deployed = bundle.member(baseline, old[row["target"]])
            versions.insert(0, ("baseline", deployed))
        for version, path in versions:
            output = HERE / ".artifacts" / ("open-" + label + "-" + version + ".json")
            records.append(capture("open-" + label + "-" + version, [sys.executable, MASTER / "scripts/lab/open_site_scan.py", path, "--json", output]))
            save("evidence/open-" + label + "-" + version + ".json", load(output))
            records.append(capture("needed-" + label + "-" + version, ["llvm-readelf", "-d", "--wide", path]))
        member = dict(label=label, targets=[item["target"] for item in composition["increments"] if (item["baseline_sha256"], item["candidate_sha256"]) == pair],
            baseline_sha256=pair[0], candidate_sha256=pair[1])
        if pair[0]:
            records.append(capture("strings-" + label, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", candidate, "--deployed", deployed]))
            output = HERE / ".artifacts" / ("abi-" + label + ".json")
            records.append(capture("abi-" + label, [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", deployed, "--new", candidate, "--calls", "--json", output,
                *[item for path in consumers for item in ["--consumer", path]]]))
            abi = load(output)
            save("evidence/abi-" + label + ".json", abi)
            member["abi_summary"] = {name: len(abi.get(name, [])) for name in ["added", "removed", "drift", "consumer_breaks", "call_diffs"]}
        else:
            member["abi_comparison"] = "No prior target: existing exact ICU new-native admission, not an invented baseline ABI PASS"
        members.append(member)
    after = {str(path): sha(path) for path in tools}
    if before != after:
        raise ValueError("Supplementary native tools changed; rerun required")
    save("native-delta-gates.json", dict(records=records, members=members, consumer_count=219, before=before, after=after,
        common_and_61b_native_bytes_identical=True, approvals_changed=False, execution_enabled=False))


if __name__ == "__main__":
    main()
