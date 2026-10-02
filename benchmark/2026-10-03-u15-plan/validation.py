import re


JARS = ["core-oj", "core-libart", "core-icu4j", "okhttp", "bouncycastle", "apache-xml",
        "adapter-mainline-stubs", "framework", "oh-adapter-framework"]
SEGMENTS = ["boot"] + ["boot-" + name for name in JARS[1:]]
IMAGE_NAMES = {segment + "." + suffix for segment in SEGMENTS for suffix in ["art", "oat", "vdex"]}
FRAMEWORK = "9e55e28623c86cc553bb2449cb18948e383a05fb0283b045d969655813b7d1b7"
OLD_FRAMEWORK = "3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af"
STUBS = "87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a"
RUNTIME_JAR = "0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4"
RUNTIME = "94c31177709dbea0b1615a63c0d41a358f7db6843cbbd11f77979576a1a86a47"
OLD_RUNTIME = "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae"
DEX2OAT = "ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b"
DRIVER = "14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46"
HOME_ID = "4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102"
BASES = {
    "common": "9b42ddc6324c63e13d494a8e1144b3c196e70dabeb5ca7a8ec4fc36b58961cd1",
    "61b": "f589844793299c3884a6738b2a4168dffe45680e89379cd53774bbde5c42835e",
}
INSTALLERS = {
    "common": "2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0",
    "61b": "51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5",
}
INSTALLER_PATHS = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def check_plan(plan, images):
    if any(plan.get(field) is not False for field in ["execution_enabled", "bake_executed", "deploy_allowed", "promotion_confirmed"]):
        raise ValueError("Preparation cannot claim execution, readiness or promotion")
    if {key: row["sha256"] for key, row in plan["content_bases"].items()} != BASES:
        raise ValueError("Wrong U14 content bases")
    rows = plan["bcp"]
    if [row["name"] for row in rows] != [name + ".jar" for name in JARS]:
        raise ValueError("Effective BCP order or member set changed")
    if any(not valid_sha(row["sha256"]) or not valid_sha(row["u14_sha256"]) for row in rows):
        raise ValueError("BCP identity incomplete")
    if [row["name"] for row in rows if row["sha256"] != row["u14_sha256"]] != ["framework.jar"]:
        raise ValueError("Not the declared single BCP swap")
    if rows[7]["sha256"] != FRAMEWORK or rows[7]["u14_sha256"] != OLD_FRAMEWORK or rows[6]["sha256"] != STUBS:
        raise ValueError("Framework or preserved stubs identity mismatch")
    if plan["runtime_jar"]["sha256"] != RUNTIME_JAR or plan["runtime_jar"]["in_bcp"] is not False:
        raise ValueError("Runtime JAR is unchanged and outside BCP")
    if len(images) != 27 or {row["name"] for row in images} != IMAGE_NAMES:
        raise ValueError("Image group must contain exactly 27 distinct members")
    if any(row["candidate_sha256"] is not None or row["rebake"] is not True or not valid_sha(row["u14_sha256"]) for row in images):
        raise ValueError("Unbaked output identity is unknown")
    if plan["actual_changed_image_count"] is not None or plan["candidate_bundle_sha256"] is not None:
        raise ValueError("No actual output or bundle identity exists yet")
    machine = plan["machine"]
    if machine["hostname"] != "ecs-9f6c" or machine["home_identity_sha256"] != HOME_ID or machine["a2hlab_use"] or machine["current_remote_verified"]:
        raise ValueError("Only approved hw248 identity is planned, not remotely verified")
    if plan["frozen_tools"]["dex2oat64"]["sha256"] != DEX2OAT or plan["frozen_tools"]["driver"]["sha256"] != DRIVER:
        raise ValueError("Frozen tool identities changed")
    if plan["transaction_base"]["common"] is not None or plan["transaction_base"]["61b"] is not None:
        raise ValueError("No implicit transaction baseline")


def check_slots(ledger):
    if ledger["execution_enabled"] or ledger["final_batch_complete"] or ledger["candidate_bundle_sha256"] is not None:
        raise ValueError("Input slots are not a complete executable batch")
    slots = {row["id"]: row for row in ledger["slots"]}
    if len(ledger["slots"]) != 3 or set(slots) != {"runtime-m3", "host-mindustry", "compat-v3"}:
        raise ValueError("Native slot set changed")
    runtime = slots["runtime-m3"]
    if runtime["sha256"] != RUNTIME or runtime["repeat_sha256"] != RUNTIME or runtime["baseline_sha256"] != OLD_RUNTIME:
        raise ValueError("M3 native runtime identity mismatch")
    if runtime["target"] != "/system/android/lib64/liboh_android_runtime.so" or runtime["state"] != "staged":
        raise ValueError("Runtime escaped its owner target")
    if any(row["applied"] for row in ledger["slots"]):
        raise ValueError("No native slot has been deployed")
    for name in ["host-mindustry", "compat-v3"]:
        row = slots[name]
        if row["state"] != "pending" or row["sha256"] is not None or row["artifact"] is not None:
            raise ValueError("Pending input cannot carry a fake candidate identity")


def check_transaction(binding, variant):
    if variant not in BASES:
        raise ValueError("Unknown board profile")
    if not binding.get("path") or not valid_sha(binding.get("sha256")):
        raise ValueError("Explicit transaction base path and full SHA required")
    evidence = binding.get("signed_identity") or {}
    if not evidence.get("path") or not valid_sha(evidence.get("sha256")) or evidence.get("approved_by") != "outer(claude)":
        raise ValueError("Signed per-board identity required; content is not promotion")
    for target in INSTALLER_PATHS:
        if binding.get("expected", {}).get(target) != INSTALLERS[variant]:
            raise ValueError("Board-local installer identity changed")


def check_receipt(receipt, inputs, outputs):
    if set(inputs) != {name + ".jar" for name in JARS} or set(outputs) != IMAGE_NAMES:
        raise ValueError("Expected receipt maps incomplete")
    for field, expected in [("input_jars", inputs), ("outputs", outputs)]:
        if receipt.get(field) != expected or not all(valid_sha(value) for value in expected.values()):
            raise ValueError("Paired receipt mismatch: " + field)
    for field in ["toolchain_identity_sha256", "build_log_sha256", "session_log_sha256", "hostlibs_sha256", "argv_sha256"]:
        if not valid_sha(receipt.get(field)):
            raise ValueError("Actual build evidence missing: " + field)
    if receipt.get("dex2oat_sha256") != DEX2OAT or receipt.get("driver_sha256") != DRIVER:
        raise ValueError("Frozen compiler or driver identity mismatch")
    if any(receipt.get(field) != 0 for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]):
        raise ValueError("Compiler or live logging failed")
    if receipt.get("status") != "verified" or not receipt.get("actual_argv"):
        raise ValueError("Template is not a verified receipt")
    if receipt.get("exception_used"):
        approval = receipt.get("u15_outer_exception_approval") or {}
        if approval.get("input_jars") != inputs or approval.get("outputs") != outputs or not valid_sha(approval.get("sha256")):
            raise ValueError("Historical exception is not automatic U15 approval")
