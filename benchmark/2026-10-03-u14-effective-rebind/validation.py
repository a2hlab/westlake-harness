import copy
import json

BASES = {
    "common": "91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28",
    "61b": "8861a11a843ac9c6278308b3c00dff4a4cfeaa08ca62e05125c7892d52d67262",
}
T8_BASES = {
    "common": "190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736",
    "61b": "c0adc4a9147b0233f03bee75604b9e17509d10bca946032ef4ca9e7e0b061ff9",
}
INSTALLER = "51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5"
INSTALLER_PATHS = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]
ABI_MEMBER = "payload/android/lib64/westlake_native/libwestlake_native_abi.so"
ABI_TARGET = "/system/android/lib64/westlake_native/libwestlake_native_abi.so"
OLD_ABI = "7605812cc5249534950bb0533baa3199b380daf6e763af12ed216c2c70649515"
FIRST_BUNDLE = "93bb674a64e0ca5290b9dfe17eb6761107a5d7a85c21a7a2a5d44cd91c53da53"


def check_base(variant, expected_hash, actual_hash, identity, mode="planned-u13"):
    pins = BASES if mode == "planned-u13" else T8_BASES if mode == "diagnostic-t8" else {}
    if variant not in pins or expected_hash != pins[variant] or actual_hash != expected_hash:
        raise ValueError("Explicit U13 variant identity mismatch")
    if variant == "61b" and any(identity["expected"].get(target) != INSTALLER for target in INSTALLER_PATHS):
        raise ValueError("61b board-local installer identity mismatch")


def check_delta(before, after, abi_sha):
    if before.keys() != after.keys():
        raise ValueError("Artifact inventory changed")
    changes = sorted(name for name in before if before[name] != after[name])
    allowed = [] if abi_sha == OLD_ABI else [ABI_MEMBER]
    if changes != allowed or after[ABI_MEMBER] != abi_sha:
        raise ValueError("Only the private native ABI slot may change")
    return changes


def semantic(finding):
    result = copy.deepcopy(finding)
    for key in ["issue_id", "package_manifest_sha256", "inputs_sha256", "disposition", "exception"]:
        result.pop(key, None)
    return json.dumps(result, sort_keys=True, separators=(",", ":"))


def map_pending(previous, current):
    mapping = {(row["gate"], semantic(row)): row for row in previous}
    return [dict(gate=row["gate"], old_issue_id=mapping.get((row["gate"], semantic(row)), {}).get("issue_id"),
        new_issue_id=row["issue_id"], semantic_unchanged=(row["gate"], semantic(row)) in mapping,
        approved_by=None, applied=False) for row in current]


def check_disabled(composition):
    if any(composition.get(key) is not False for key in ["promotion_confirmed", "execution_enabled", "rollout_ready"]):
        raise ValueError("Conditional package cannot claim promotion or execution")


def check_local_plan(plan, identity):
    for target in INSTALLER_PATHS:
        expected = identity["expected"][target]
        if plan["baseline"].get(target) != expected or plan["expected"].get(target) != expected:
            raise ValueError("Installer transaction identity changed")
        if any((row if isinstance(row, str) else row.get("target")) == target for group in ["changes", "additions"] for row in plan[group]):
            raise ValueError("Board-local installer must not be installed")


def check_image_approval(approval, draft_sha, jars, outputs, draft):
    if approval.get("decision") != "approve" or approval.get("signer") != "outer(claude)" or draft_sha not in approval.get("object", ""):
        raise ValueError("Exact outer image approval object mismatch")
    if draft["input_jars"] != jars or draft["outputs"] != outputs:
        raise ValueError("Image approval input/output pair mismatch")
    if draft["object"]["file_offset_start"] != "0x3e3b8" or draft["object"]["file_offset_end_exclusive"] != "0x3e3c0":
        raise ValueError("Image approval interval mismatch")
