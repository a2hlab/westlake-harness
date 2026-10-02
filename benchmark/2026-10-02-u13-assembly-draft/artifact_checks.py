"""Full effective ELF inventory and exact U12-to-U13 static delta; no admission writes."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import sys

from common import BASE, HERE, MASTER, PACKAGE, capture, portable, save, sha
import generation_bundle as gb
import generation_static_checks as static


def edge_signature(row):
    return json.dumps({name: value for name, value in row.items() if name not in {"pc", "binary", "inherit_after_open"}}, sort_keys=True)


def edge_delta(before, after):
    old = Counter(edge_signature(row) for row in before)
    new = Counter(edge_signature(row) for row in after)
    return dict(added=[json.loads(value) for value, count in sorted((new - old).items()) for _ in range(count)], removed=[json.loads(value) for value, count in sorted((old - new).items()) for _ in range(count)])


def scan_one(item):
    digest, source = item
    output = HERE / ".artifacts/full-scans" / (digest + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, MASTER / "scripts/lab/open_site_scan.py", source, "--json", output]
    record = capture("scan-" + digest, command, timeout=600)
    if record["exit_code"] != 0:
        raise ValueError("full-package scan failed: " + digest)
    data = json.loads(output.read_text())
    binary = data["binaries"][0]
    return digest, dict(sha256=digest, source=portable(source), json=portable(output), json_sha256=sha(output), raw=record["raw"], raw_sha256=record["raw_sha256"], exit_code=record["exit_code"], sites=binary["sites"], namespace_edges=binary["namespace_edges"], findings=data["findings"])


def main():
    old, new = static.effective(BASE), static.effective(PACKAGE)
    unique, targets = {}, []
    for target, row in sorted(new.items()):
        source = gb.member(PACKAGE, row)
        if source.read_bytes()[:4] != b"\x7fELF":
            continue
        before = gb.member(BASE, old[target])
        unique.setdefault(row["sha256"], source)
        unique.setdefault(old[target]["sha256"], before)
        targets.append(dict(target=target, before=old[target]["sha256"], after=row["sha256"], changed=row["sha256"] != old[target]["sha256"]))
    print(f"Full-package scan: {len(targets)} targets, {len(unique)} unique ELF bytes", flush=True)
    scans = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for digest, result in pool.map(scan_one, unique.items()):
            scans[digest] = result
            print(f"scanned {len(scans)}/{len(unique)} {digest[:12]} open={len(result['sites'])} edges={len(result['namespace_edges'])}", flush=True)
    changes = []
    for row in targets:
        before, after = scans[row["before"]], scans[row["after"]]
        row.update(open_before=len(before["sites"]), open_after=len(after["sites"]), edges_before=len(before["namespace_edges"]), edges_after=len(after["namespace_edges"]), findings_before=dict(Counter(value["kind"] for value in before["findings"])), findings_after=dict(Counter(value["kind"] for value in after["findings"])))
        if row["changed"]:
            row["open_delta"] = static.site_delta(before["sites"], after["sites"])
            row["namespace_edge_delta"] = edge_delta(before["namespace_edges"], after["namespace_edges"])
            changes.append(row)
    inventory = {digest: {name: value for name, value in result.items() if name not in {"sites", "namespace_edges", "findings"}} for digest, result in scans.items()}
    save("full-package-open-sites.json", dict(bundle_sha256=sha(PACKAGE / "bundle.json"), target_count=len(targets), unique_elf_count=len(scans), targets=targets, scans=inventory, changed_targets=changes, execution_enabled=False, cache_scope="Verified identical bytes reuse one scan; every baseline and candidate target retained, including unchanged aliases"))
    changed = json.loads((HERE / "composition.json").read_text())["board_changes"]
    checks = []
    for target, row in changed.items():
        suffix = "-route" if "/route-a/" in target else "-root"
        stem = target.rsplit("/", 1)[-1] + suffix
        before, after = gb.member(BASE, old[target]), gb.member(PACKAGE, new[target])
        checks.append(dict(target=target, deployed_sha256=sha(before), candidate_sha256=sha(after), abi=capture("abi-" + stem, [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", before, "--new", after, "--calls", "--json", HERE / "evidence" / ("abi-" + stem + ".json")]), strings=capture("strings-" + stem, [sys.executable, MASTER / "scripts/lab/deployed_strings_diff.py", after, "--deployed", before])))
    report = static.check(PACKAGE, BASE, {})
    save("static-checks.json", report)
    save("artifact-checks.json", checks)
    review = []
    for row in report["members"]:
        if row["status"] != "PASS":
            review.append({name: row.get(name) for name in ["target", "candidate_sha256", "deployed_sha256", "delta_sha256", "open_site_delta", "status"]})
    save("static-outer-review.json", dict(bundle_sha256=sha(PACKAGE / "bundle.json"), review_required=review, approved_by=None, execution_enabled=False, reason="No outer approval has been fabricated; proposed policy must bind exact pair and delta before production acceptance"))
    print(json.dumps(dict(full_targets=len(targets), unique_elfs=len(scans), changed_targets=len(changes), static_status=report["status"], review_required=len(review)), indent=2))


if __name__ == "__main__":
    main()
