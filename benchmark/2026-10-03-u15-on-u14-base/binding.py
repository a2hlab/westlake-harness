import copy
import re

INSTALLERS = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]


def check_base(variant, expected_sha, actual_sha, data, reviewed, identities):
    if variant not in identities or actual_sha != expected_sha or not re.fullmatch(r"[a-f0-9]{64}", expected_sha):
        raise ValueError("Explicit per-board BASE identity mismatch")
    candidate_sha = identities[variant]["candidate_bundle_sha256"]
    if actual_sha == candidate_sha:
        if data != reviewed:
            raise ValueError("Reviewed candidate metadata changed")
        return
    normalized = copy.deepcopy(data)
    for name in ["rollout_ready", "rollout_blocker"]:
        normalized[name] = reviewed[name]
    if data.get("rollout_ready") is not True or normalized != reviewed:
        raise ValueError("Future armed BASE changes more than arming metadata")


def check_plan(plan, expected):
    for target in INSTALLERS:
        if plan["baseline"].get(target) != expected[target] or plan["expected"].get(target) != expected[target]:
            raise ValueError("Board-local installer identity changed")
        for field in ["changes", "additions"]:
            if any((row if isinstance(row, str) else row["target"]) == target for row in plan[field]):
                raise ValueError("Installer action is forbidden")
    if plan["rollout_ready"]:
        raise ValueError("U15 must stay disabled")


def check_artifacts(previous, current):
    if previous != current:
        raise ValueError("Metadata-only binding changed candidate artifacts")
