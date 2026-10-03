import csv
import json
import subprocess
import sys

from native_pair import FLUTTER, FLUTTER_SHA, PAIR
from native_static import capture
from prepare import HERE, MASTER, WS, save, sha
import generation_static_checks as static

KEYS_SHA = "6f42bf0a5265da6709c63698adb5f97c7bffd1e18e9fa70c37dae64c00239d38"
TOOL_SHA = "01f0b55a3d0ec6b4aa0a7fa9614a63123617f1c9ca8f5d337314a97ccbc5a22e"
TOOL_COMMIT = "770ef6e9e4fa0aa2a240c38578957a9fca12924d"


def expand(value):
    return WS / value.removeprefix("$WORKSPACES/")


def main():
    keys = MASTER / "benchmark/2026-10-03-u16-observation-keys/u16-stage-a-keys.json"
    tool_repo = WS / "westlake-harness-t4"
    tool = tool_repo / "scripts/lab/check_fix_observers.py"
    if sha(keys) != KEYS_SHA or sha(tool) != TOOL_SHA:
        raise ValueError("Observation keys or actual observer checker drifted")
    original_tool = subprocess.run(["git", "-C", tool_repo, "show", TOOL_COMMIT + ":scripts/lab/check_fix_observers.py"],
        check=True, stdout=subprocess.PIPE).stdout
    if original_tool != tool.read_bytes():
        raise ValueError("Observer checker not identical to pinned committed v3")
    binding = json.loads((HERE / "native-pair-binding.json").read_text())
    old_binding = json.loads((HERE / "inputs/history-pair-b1c9/native-pair-binding.json").read_text())
    old_pair = expand(old_binding["staging"])
    if sha(old_pair / "package.json") != old_binding["native_manifest_sha256"]:
        raise ValueError("Historical b1c9 staging manifest changed")
    old_manifest = json.loads((old_pair / "package.json").read_text())
    candidate = json.loads((PAIR / "package.json").read_text())
    changed_members = [name for name, digest in candidate["files"].items() if old_manifest["files"].get(name) != digest]
    if changed_members != [FLUTTER] or candidate["files"].keys() != old_manifest["files"].keys():
        raise ValueError("A3 substitution must change only the Flutter payload")
    for package, manifest in [(old_pair, old_manifest), (PAIR, candidate)]:
        for name, digest in manifest["files"].items():
            if sha(package / name) != digest:
                raise ValueError("Immutable historical or selected native inventory changed")
    save("flutter-replacement-proof.json", dict(old_manifest_sha256=old_binding["native_manifest_sha256"],
        candidate_manifest_sha256=binding["native_manifest_sha256"], changed_members=changed_members,
        checked_payloads_per_version=len(candidate["files"]),
        old_flutter_sha256=old_manifest["files"][FLUTTER], candidate_flutter_sha256=FLUTTER_SHA,
        westlake_native_sha256=candidate["files"]["payload/android/lib64/westlake_native/libandroid.so"],
        runtime_unchanged_from_b1c9_staging=True, original_staging_unchanged=True, execution_enabled=False))
    plan = json.loads((HERE / "plan.json").read_text())
    rows = []
    candidate_sources = {}
    for variant, reference in plan["content_bases"].items():
        base = expand(reference["path"])
        if sha(base / "bundle.json") != reference["sha256"]:
            raise ValueError("Per-board U15 content base drifted")
        effective = static.effective(base)
        for member, change in binding["changes"].items():
            target = "/system/android/lib64/" + member.removeprefix("payload/android/lib64/")
            if effective[target]["sha256"] != change["old"] or sha(PAIR / member) != change["new"]:
                raise ValueError("Native increment baseline or payload mismatch")
            rows.append(dict(variant=variant, layer="native", target=target, operation="replace",
                baseline_sha256=change["old"], candidate_sha256=change["new"]))
            candidate_sources[target] = dict(source=PAIR / member, sha256=change["new"])
        for item in [plan["bcp"][6], plan["runtime_jar"]]:
            if effective[item["target"]]["sha256"] != item["u15_sha256"] or sha(expand(item["snapshot"])) != item["sha256"]:
                raise ValueError("JAR increment baseline or snapshot mismatch")
            rows.append(dict(variant=variant, layer="JAR", target=item["target"], operation="replace",
                baseline_sha256=item["u15_sha256"], candidate_sha256=item["sha256"]))
            candidate_sources[item["target"]] = dict(source=expand(item["snapshot"]), sha256=item["sha256"])
    if len(rows) != 8 or any(row["candidate_sha256"] != FLUTTER_SHA for row in rows if row["target"].endswith("westlake_flutter/libandroid.so")):
        raise ValueError("Exactly four arrived increments per variant required")
    with (HERE / "increments.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["variant", "layer", "target", "operation", "baseline_sha256", "candidate_sha256"])
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["variant"], row["target"])))
    keys_snapshot = HERE / "inputs/observers/u16-stage-a-keys.json"
    keys_snapshot.parent.mkdir(parents=True, exist_ok=True)
    keys_snapshot.write_bytes(keys.read_bytes())
    tool_snapshot = HERE / "inputs/observers/check_fix_observers.py.txt"
    tool_snapshot.write_bytes(tool.read_bytes())
    record = capture("u16-a3-fix-observers", [sys.executable, tool, HERE / "increments.csv", keys,
        "--csv", HERE / "fix-observers.csv"])
    with (HERE / "fix-observers.csv").open() as stream:
        observations = list(csv.DictReader(stream))
    gaps = [row for row in observations if row["status"] != "OK"]
    save("fix-observer-receipt.json", dict(records=[record], increments_sha256=sha(HERE / "increments.csv"),
        keys=keys, keys_sha256=KEYS_SHA, checker=tool, checker_sha256=TOOL_SHA, checker_commit=TOOL_COMMIT,
        checker_snapshot_sha256=sha(tool_snapshot), checker_note="Master worktree has no check_fix_observers.py; exact committed oc-t4 v3 used read-only, no tool edits",
        candidate_sources=candidate_sources, artifacts=len(observations), gaps=len(gaps), matrix_sha256=sha(HERE / "fix-observers.csv"),
        scope="8 known changed files across two content variants; 27 image outputs unbaked and not assigned invented hashes",
        images_pending=27, full_bundle_coverage_claimed=False, execution_enabled=False, rollout_ready=False, board_access=False))
    if record["exit_code"] != 0 or len(observations) != 8 or gaps:
        raise ValueError("Observer matrix refused; raw output retained")
    print("OBSERVERS PASS: 8 arrived increments,0 GAP; keys6f42bf0a;27 images pending; disabled")


if __name__ == "__main__":
    main()
