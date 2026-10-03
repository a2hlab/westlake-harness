import copy


INSTALLERS = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]


def check_base(variant, expected_sha, actual_sha, data, signed, identities):
    if variant not in identities or actual_sha != expected_sha:
        raise ValueError("Explicit per-board BASE hash mismatch")
    pins = identities[variant]
    if actual_sha not in [pins["signed_unarmed_bundle_sha256"], pins["actual_armed_bundle_sha256"]]:
        raise ValueError("BASE is not the reviewed per-board U13 identity")
    normalized = copy.deepcopy(data)
    for name in ["rollout_ready", "rollout_blocker"]:
        normalized[name] = signed[name]
    if normalized != signed:
        raise ValueError("U13 correspondence changes more than arming metadata")
    if actual_sha == pins["signed_unarmed_bundle_sha256"] and data != signed:
        raise ValueError("Signed unarmed U13 metadata changed")


def check_plan(plan, expected):
    for target in INSTALLERS:
        if plan["baseline"].get(target) != expected[target] or plan["expected"].get(target) != expected[target]:
            raise ValueError("Board-local installer identity changed")
        for name in ["changes", "additions"]:
            if any((row if isinstance(row, str) else row["target"]) == target for row in plan[name]):
                raise ValueError("Installer action is forbidden")
    if plan["rollout_ready"]:
        raise ValueError("U14 must remain disabled")


def check_artifacts(previous, current):
    if previous != current:
        raise ValueError("Metadata-only rebinding changed candidate artifact bytes")
