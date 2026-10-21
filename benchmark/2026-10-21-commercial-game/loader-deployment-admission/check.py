#!/usr/bin/env python3
"""Offline G19 evidence check; never executes deployment code or contacts a device."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7"
CANDIDATE = "878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23"
BOOT = "a1d869b4-69a2-40a4-937e-4860f5b54239"
TARGETS = {
    "/system/android/lib64/libnativeloader.so": "/data/westlake-demo/u13/sources/seq16",
    "/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libnativeloader.so": "/data/westlake-demo/u13/sources/seq51",
}


def read_json(name):
    return json.loads((ROOT / name).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(admission):
    errors = []

    def require(condition, label):
        if not condition:
            errors.append(label)

    # Validate actual archived bytes, not the earlier validation.json PASS claim.
    for row in read_json("source-index.json")["files"]:
        require(digest(ROOT / row["archive"]) == row["archive_sha256"],
                "archive_pin:" + row["archive"])
    for row in read_json("outer-readonly-01/commands.json"):
        require(row["rc"] == 0, "outer_rc:" + row["name"])
        for stream in ("stdout", "stderr"):
            name = "outer-readonly-01/" + row["name"] + "." + stream + ".txt"
            require(digest(ROOT / name) == row[stream + "_sha256"], "outer_pin:" + name)

    boots = [(ROOT / name).read_text().strip() for name in (
        "outer-readonly-01/boot-before.stdout.txt",
        "outer-readonly-01/boot-after.stdout.txt",
        "outer-fingerprint-01/before-boot.stdout",
        "outer-fingerprint-01/after-boot.stdout",
    )]
    require(all(value == BOOT for value in boots), "fresh_boot_receipts")
    require(admission.get("boot_id") == BOOT, "boot_binding")
    require(admission.get("deployment_ready") is False, "undeployed_status")
    require(admission.get("device_writes") is False, "no_device_writes")
    require(admission.get("push") is False, "no_push")
    require(admission.get("fresh_transaction_without_historical_owned_state") is True,
            "new_transaction_qualification")
    require(admission.get("unique_winner_blocks_paired_publication") is False,
            "winner_not_a_pairing_gate")

    aliases = admission.get("aliases", [])
    require(len(aliases) == 2 and {r.get("target") for r in aliases} == set(TARGETS),
            "alias_set")
    hashes = dict((parts[1], parts[0]) for line in
                  (ROOT / "outer-readonly-01/hashes.stdout.txt").read_text().splitlines()
                  if len(parts := line.split()) == 2)
    mounts = [line.split() for line in
              (ROOT / "outer-readonly-01/mountinfo.stdout.txt").read_text().splitlines()]
    for row in aliases:
        target = row.get("target")
        require(target in TARGETS, "alias_target")
        require(row.get("baseline_sha256") == BASELINE == hashes.get(target), "baseline_pin")
        require(row.get("candidate_sha256") == CANDIDATE, "candidate_pin")
        source = TARGETS.get(target)
        require(row.get("observed_mount_source") == source and source is not None,
                "mount_source_pin")
        require(any(len(m) > 4 and m[4] == target and "/data" + m[3] == source
                    for m in mounts), "mount_source_receipt")
        require(bool(row.get("restoration")), "restoration_missing")

    artifacts = read_json("g18/build-01-receipt.json")["artifacts"]
    require(artifacts["baseline"]["sha256"] == BASELINE, "build_baseline_pin")
    require(artifacts["candidate"]["sha256"] == CANDIDATE, "build_candidate_pin")
    objects = {r["label"]: r for r in read_json("objects.json")}
    for label in ("g18_baseline", "u13_system", "u13_route"):
        require(objects[label]["sha256"] == BASELINE, "object_pin:" + label)
    require(objects["g18_candidate"]["sha256"] == CANDIDATE, "object_pin:g18_candidate")
    manifest = read_json("u13-original/native/package.json")
    for source in ("payload/android/lib64/libnativeloader.so", "payload/route/libnativeloader.so"):
        require(manifest["files"].get(source) == BASELINE, "manifest_pin:" + source)

    fp = read_json("outer-fingerprint-01/fingerprint.stdout")
    require((fp["runtime_files"], fp["boot_files"]) == (124, 36), "fingerprint_coverage")
    for key in ("runtime_files", "boot_files", "runtime_fp", "boot_fp"):
        require(admission["fingerprint"][key] == fp[key], "fingerprint_binding:" + key)
    # 285-target receipt remains an explicitly attributed outer observation.
    # Do not silently promote it to a check performed here or reopen private/G20 inputs.
    outer = admission["full_baseline_outer_receipt"]
    require((outer["targets"], outer["verified"], outer["batches"], outer["all_remote_rc"])
            == (285, 285, 9, 0), "outer_attributed_counts")
    require(BOOT.startswith(outer["same_boot"]) and "not reread" in outer["authority"],
            "outer_attribution")
    return errors


def run(admission):
    errors = validate(admission)
    negatives = []
    mutations = [
        ("missing_alias", lambda a: a["aliases"].pop(), {"alias_set"}),
        ("old_boot_fake_ready", lambda a: a.update(boot_id="old-boot", deployment_ready=True),
         {"boot_binding", "undeployed_status"}),
        ("old_boot_only", lambda a: a.update(boot_id="old-boot"), {"boot_binding"}),
        ("fake_ready_only", lambda a: a.update(deployment_ready=True), {"undeployed_status"}),
        ("candidate_pin_drift", lambda a: a["aliases"][0].update(candidate_sha256="0" * 64),
         {"candidate_pin"}),
        ("mount_source_drift", lambda a: a["aliases"][0].update(observed_mount_source="/data/unowned"),
         {"mount_source_pin"}),
    ]
    for name, mutate, expected in mutations:
        changed = copy.deepcopy(admission)
        mutate(changed)
        reasons = validate(changed)
        passed = expected.issubset(set(reasons))
        negatives.append(dict(name=name, rejected=bool(reasons), expected_reasons=sorted(expected),
                              actual_reasons=reasons, passed=passed))
    return dict(status="PASS" if not errors and all(r["passed"] for r in negatives) else "FAIL",
                scope="offline archived admission evidence; not deployment or game acceptance",
                positive_errors=errors, negative_cases=negatives,
                device_io=False, u7_preflight_run=False, g18_regressions_repeated=False,
                full_baseline_285="outer-attributed only; not reread",
                checker_sha256=digest(Path(__file__)),
                admission_sha256=hashlib.sha256(json.dumps(admission, sort_keys=True).encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, default=ROOT / "admission.json")
    args = parser.parse_args()
    try:
        result = run(json.loads(args.admission.read_text()))
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "FAIL", "error": str(error), "device_io": False}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
