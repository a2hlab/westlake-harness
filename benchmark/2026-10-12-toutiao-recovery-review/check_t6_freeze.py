import hashlib
import json
import os
from pathlib import Path
import sys


REVIEW = Path(__file__).resolve().parent
WORKSPACES = REVIEW.parents[1].parent
REPO = WORKSPACES / "westlake-harness-t4"
ROOT = REPO / "benchmark/2026-10-12-exact-realization"
EXPECTED_FREEZE = "3791b700da9f5d139fc40bdfc81396a0b22e50aef9ecf38e080f8db605a84e27"
EXECUTOR = "496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d"


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def source_path(value, base):
    if value.startswith("$WORKSPACES/"):
        return WORKSPACES / value[len("$WORKSPACES/"):]
    path = Path(value)
    return path if path.is_absolute() else base / path


def main():
    check(digest(ROOT / "freeze.json") == EXPECTED_FREEZE, "freeze identity changed")
    freeze = read(ROOT / "freeze.json")
    frozen = {}
    for row in freeze["files"]:
        path = REPO / row["path"]
        check(row["path"] not in frozen, "duplicate frozen path")
        check(path.is_file() and not path.is_symlink(), "frozen path shape")
        check(digest(path) == row["sha256"] and path.stat().st_size == row["bytes"], row["path"])
        frozen[row["path"]] = row["sha256"]
    listing = (ROOT / "landing-paths.txt").read_text().splitlines()
    prefix = "benchmark/2026-10-12-exact-realization/"
    check(len(listing) == len(set(listing)) == 52, "landing count/duplicates")
    check(set(listing) == set(frozen) | {prefix + "freeze.json", prefix + "landing-paths.txt"}, "freeze/landing closure")
    before = read(REVIEW / "evidence/base-placement/t6-narrow-preview.json")["source_sha256"]
    delta = {name: {"before": sha, "after": digest(ROOT / name)} for name, sha in before.items()}
    check(all(row["before"] == row["after"] for row in delta.values()), "eight-file code delta requires targeted re-review")
    artifact_rows = read(ROOT / "artifact-pins.json")["artifacts"]
    for row in artifact_rows.values():
        path = source_path(row["path"], ROOT)
        check(digest(path) == row["sha256"] and path.stat().st_size == row["bytes"], "artifact pin drift")
    proof = read(ROOT / "output-5cd-placement/realization.json")
    check(proof["status"] == "candidate/not_sealed" and proof["source_seal"] is None, "false seal identity")
    check(proof["execution_enabled"] is False and proof["signature"] is None, "unexpected proof authority")
    request_path = Path(proof["request"]["path"])
    check(digest(request_path) == proof["request"]["sha256"], "request pin")
    request = read(request_path)
    check(digest(source_path(proof["generator"]["path"], ROOT)) == proof["generator"]["sha256"], "generator pin")
    for row in request["v6"].values():
        check(digest(source_path(row["path"], ROOT)) == row["sha256"], "v6 input pin")
    identity = source_path(request["source_identity"]["path"], request_path.parent)
    check(digest(identity) == request["source_identity"]["sha256"], "source fingerprint pin")
    identity_data = read(identity)
    check(identity_data["status"] == "candidate/not_sealed" and len(identity_data["files"]) == 806, "origin identity/count")
    check(len(proof["files"]) == len({row["target"] for row in proof["files"]}) == 806, "proof complete target set")
    sys.dont_write_bytecode = True
    os.environ["WORKSPACES"] = str(WORKSPACES)
    sys.path.insert(0, str(ROOT))
    import observations
    validated = observations.validate(request["parameter_evidence"], request_path.parent, request["parameters"], "placement")
    check(validated == proof["parameter_evidence"] and not validated["synthetic"], "real parameter evidence mismatch")
    check(validated["host_uid"] == validated["host_gid"] == 20011300 and validated["window_id"] is None, "5cd placement parameters")
    packages = {}
    physical_bytes = 0
    for name in ("output-5cd-placement/package", "output-restoration-preview"):
        package = ROOT / name
        manifest = read(package / "manifest.json")
        for row in manifest["files"]:
            path = package / row["path"]
            check(path.is_file() and not path.is_symlink(), "package source shape: " + row["path"])
            check(digest(path) == row["sha256"], "physical package SHA: " + row["path"])
            if "bytes" in row:
                check(path.stat().st_size == row["bytes"], "physical package size")
            physical_bytes += path.stat().st_size
        plan = read(package / "plan.json")
        check(len(plan["members"]) == len({row["target"] for row in plan["members"]}) == 487, "487 exact target closure")
        for row in plan["members"]:
            path = package / row["source"].removeprefix("$PACKAGE/")
            check(digest(path) == row["sha256"], "plan target actual SHA: " + row["target"])
        check(digest(package / "executor.py") == EXECUTOR, "original transaction executor changed")
        packages[name] = {"plan": plan, "manifest": digest(package / "manifest.json"), "plan_sha256": digest(package / "plan.json")}
    disabled = packages["output-5cd-placement/package"]["plan"]
    preview = packages["output-restoration-preview"]["plan"]
    check(disabled["execution_enabled"] is False and preview["execution_enabled"] is True, "prospective plan state")
    preview_by_target = {row["target"]: row for row in preview["members"]}
    changed_targets = []
    for row in disabled["members"]:
        after = preview_by_target[row["target"]]
        check({key: value for key, value in row.items() if key != "sha256"} ==
              {key: value for key, value in after.items() if key != "sha256"}, "member metadata/preimage/prerequisite changed")
        if row["sha256"] != after["sha256"]:
            changed_targets.append(row["target"])
    check(len(changed_targets) == 2 and {Path(value).name for value in changed_targets} == {"startup.env", "startup.expected.sha256"}, "unexpected activation delta")
    check({key: value for key, value in disabled.items() if key not in {"members", "execution_enabled"}} ==
          {key: value for key, value in preview.items() if key not in {"members", "execution_enabled"}}, "transaction fields changed")
    clean = read(ROOT / "evidence/clean-replay/receipt.json")
    check(clean["rc"] == 0 and clean["device_calls"] == 0, "producer clean replay failed")
    for row in clean["copied"]:
        check(frozen[row["path"]] == row["sha256"], "clean replay versus freeze drift")
    check(digest(ROOT / "freeze.json") == EXPECTED_FREEZE, "freeze changed during review")
    result = {"verdict": "OFFLINE_RELEASE_ACCEPT_REQUIRES_OUTER_EXECUTION_ADMISSION", "freeze_sha256": EXPECTED_FREEZE,
              "landing_sha256": digest(ROOT / "landing-paths.txt"), "frozen_files": len(frozen), "landing_files": len(listing),
              "eight_file_delta": delta, "behavior_tests_repeated": 0, "physical_bytes_hashed": physical_bytes,
              "route_targets": 487, "proof_targets": 806, "executor_sha256": EXECUTOR,
              "parameters": validated, "proof_sha256": digest(ROOT / "output-5cd-placement/realization.json"),
              "preview_manifest_sha256": packages["output-restoration-preview"]["manifest"],
              "preview_plan_sha256": packages["output-restoration-preview"]["plan_sha256"],
              "activation_changed_targets": changed_targets, "producer_clean_replay_rc": clean["rc"],
              "device_access": False, "sealed": False, "execution_authorized": False}
    output = REVIEW / "evidence/base-placement/t6-freeze-final.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
