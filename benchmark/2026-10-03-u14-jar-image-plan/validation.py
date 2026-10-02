import re


SEGMENTS = ["boot", "boot-core-libart", "boot-core-icu4j", "boot-okhttp", "boot-bouncycastle",
            "boot-apache-xml", "boot-adapter-mainline-stubs", "boot-framework", "boot-oh-adapter-framework"]
JARS = ["core-oj", "core-libart", "core-icu4j", "okhttp", "bouncycastle", "apache-xml",
        "adapter-mainline-stubs", "framework", "oh-adapter-framework"]
IMAGE_NAMES = {segment + "." + suffix for segment in SEGMENTS for suffix in ["art", "oat", "vdex"]}
STUBS = "87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a"
RUNTIME = "0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4"
HOST = "341c12608091246a09e973214b197eaf7d5b6b3f0bf9cc6ebbf3392648d338da"
DEX2OAT = "ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b"
DRIVER = "14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46"


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def check_plan(plan, images):
    if plan["execution_enabled"] or plan["bake_executed"] or plan["deploy_allowed"]:
        raise ValueError("Preparation cannot claim execution or readiness")
    rows = plan["bcp"]
    if [row["name"] for row in rows] != [name + ".jar" for name in JARS]:
        raise ValueError("Effective BCP order or member set changed")
    if any(not valid_sha(row["sha256"]) for row in rows):
        raise ValueError("BCP identity incomplete")
    changed = [row["name"] for row in rows if row["sha256"] != row["u13_sha256"]]
    if changed != ["adapter-mainline-stubs.jar"] or rows[6]["sha256"] != STUBS:
        raise ValueError("Not the declared single BCP swap")
    if plan["runtime"]["sha256"] != RUNTIME or plan["runtime"]["in_bcp"]:
        raise ValueError("Runtime JAR is not a BCP input")
    if len(images) != 27 or {row["name"] for row in images} != IMAGE_NAMES:
        raise ValueError("Image group must contain exactly 27 distinct members")
    if any(row["candidate_sha256"] is not None or not row["rebake"] for row in images):
        raise ValueError("Unbaked outputs cannot carry invented hashes")
    if plan["machine"]["selected"] != "hw248" or plan["machine"]["current_remote_verified"]:
        raise ValueError("Remote availability was not probed in this offline plan")


def check_receipt(receipt, inputs, outputs):
    if set(inputs) != {name + ".jar" for name in JARS} or set(outputs) != IMAGE_NAMES:
        raise ValueError("Expected receipt maps incomplete")
    for field, expected in [("input_jars", inputs), ("outputs", outputs)]:
        if receipt.get(field) != expected or not all(valid_sha(value) for value in expected.values()):
            raise ValueError("Paired receipt mismatch: " + field)
    for field in ["toolchain_identity_sha256", "build_log_sha256", "session_log_sha256"]:
        if not valid_sha(receipt.get(field)):
            raise ValueError("Actual build evidence missing: " + field)
    if receipt.get("dex2oat_sha256") != DEX2OAT or receipt.get("driver_sha256") != DRIVER:
        raise ValueError("Frozen compiler or driver identity mismatch")
    if any(receipt.get(field) != 0 for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code"]):
        raise ValueError("Compiler or live logging failed")
    if receipt.get("status") != "verified" or not receipt.get("build_command"):
        raise ValueError("Template or retrospective inventory is not a verified receipt")
    if receipt.get("exception_used") and not receipt.get("u14_outer_exception_approval"):
        raise ValueError("Historical backtrace exception is not automatic U14 approval")


def check_slots(ledger):
    if ledger["execution_enabled"] or ledger["final_batch_complete"]:
        raise ValueError("Input slots are not a complete executable batch")
    slots = {row["id"]: row for row in ledger["slots"]}
    if len(ledger["slots"]) != 4 or set(slots) != {"stock-host-app-ns", "flutter-private-libandroid", "native-abi-gecko", "icu-wall-two"}:
        raise ValueError("Native input slot set changed")
    host = slots["stock-host-app-ns"]
    if host["sha256"] != HOST or host["repeat_sha256"] != HOST or host["applied"]:
        raise ValueError("Host must be double-verified and staged only")
    if host["baseline_reproduction"] != "outer-approved semantic A-prime, not byte-identical":
        raise ValueError("Do not invent byte reproduction of host2a871")
    for row in ledger["slots"]:
        if row["applied"]:
            raise ValueError("No new slot has been composed")
        if row["state"] == "pending" and row["sha256"] is not None:
            raise ValueError("Pending input cannot carry a fake candidate identity")
    expected = {
        "flutter-private-libandroid": "fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5",
        "native-abi-gecko": "7605812cc5249534950bb0533baa3199b380daf6e763af12ed216c2c70649515",
        "icu-wall-two": "9b36b989dd10f29434cc60b6b7d1895878442d07f1d6b0674db9b1379420d93f"}
    for name, digest in expected.items():
        row = slots[name]
        if row["state"] == "staged" and (row["sha256"] != digest or row["artifact"]["sha256"] != digest):
            raise ValueError("Staged native identity mismatch: " + name)
    if slots["flutter-private-libandroid"].get("target") != "/system/android/lib64/westlake_flutter/libandroid.so":
        raise ValueError("Flutter change escaped its private scope")
    if slots["native-abi-gecko"].get("target") != "/system/android/lib64/westlake_native/libwestlake_native_abi.so":
        raise ValueError("Gecko change escaped its private scope")
    icu = slots["icu-wall-two"]
    if icu["state"] == "staged":
        if icu["new_dependency"]["sha256"] != "4886bc5c2b4ef0486ecda6fa3248ace4af6a1c57ed7029b17cfd4868ad2c92af":
            raise ValueError("ICU shim identity mismatch")
        if set(icu["targets"]) != {"/system/android/lib64/libicuuc.so", "/system/android/lib64/libicuuc.z.so"}:
            raise ValueError("ICU paired aliases must move together")
