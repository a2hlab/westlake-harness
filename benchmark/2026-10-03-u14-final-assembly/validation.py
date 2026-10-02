import re

BRIDGE = "7daa5435333ab99c2360dfe5ad5b75180ba0b8118d4f69f6750764c01b546452"
HOST = "341c12608091246a09e973214b197eaf7d5b6b3f0bf9cc6ebbf3392648d338da"
FLUTTER = "fff9be3190f1b1c99c3fd4559d258cbac131fb657d10b1fa7060f61c4002d5e5"
GECKO = "7605812cc5249534950bb0533baa3199b380daf6e763af12ed216c2c70649515"
ICU = "9b36b989dd10f29434cc60b6b7d1895878442d07f1d6b0674db9b1379420d93f"
SHIM = "4886bc5c2b4ef0486ecda6fa3248ace4af6a1c57ed7029b17cfd4868ad2c92af"
RUNTIME = "0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4"
STUBS = "87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a"
PREFIX = "payload/android/"
CHANGES = {
    PREFIX + "lib64/liboh_adapter_bridge.so": BRIDGE,
    "payload/runtime/appspawn-x": HOST,
    PREFIX + "lib64/westlake_flutter/libandroid.so": FLUTTER,
    PREFIX + "lib64/westlake_native/libwestlake_native_abi.so": GECKO,
    PREFIX + "lib64/libicuuc.so": ICU,
    PREFIX + "lib64/libicuuc.z.so": ICU,
    PREFIX + "framework/oh-adapter-runtime.jar": RUNTIME,
    PREFIX + "framework/adapter-mainline-stubs.jar": STUBS,
}
ADDITIONS = {PREFIX + "lib64/libicu74compat.so": SHIM}
JARS = ["core-oj", "core-libart", "core-icu4j", "okhttp", "bouncycastle", "apache-xml", "adapter-mainline-stubs", "framework", "oh-adapter-framework"]
SEGMENTS = ["boot", "boot-core-libart", "boot-core-icu4j", "boot-okhttp", "boot-bouncycastle", "boot-apache-xml", "boot-adapter-mainline-stubs", "boot-framework", "boot-oh-adapter-framework"]
IMAGES = {segment + "." + suffix for segment in SEGMENTS for suffix in ["art", "oat", "vdex"]}


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def check_partial(old, new, state, descriptor_exists=False):
    changed = {name: digest for name, digest in new.items() if name in old and old[name] != digest}
    added = {name: digest for name, digest in new.items() if name not in old}
    if changed != CHANGES or added != ADDITIONS or set(old) - set(new):
        raise ValueError("Selected native/JAR scope or artifact identity drift")
    if descriptor_exists or state.get("execution_enabled") is not False or state.get("final_batch_complete") is not False:
        raise ValueError("Partial composition must not be executable")
    if state.get("images") != "pending" or state.get("paired_receipt") is not None:
        raise ValueError("Old images and historical receipt cannot attest U14")


def check_transaction(path, expected, actual):
    if not path or not valid_sha(expected) or expected != actual:
        raise ValueError("Explicit transaction baseline identity required")


def check_receipt(receipt, inputs, outputs):
    if set(inputs) != {name + ".jar" for name in JARS} or set(outputs) != IMAGES:
        raise ValueError("Incomplete paired inventories")
    if receipt.get("input_jars") != inputs or receipt.get("outputs") != outputs:
        raise ValueError("Receipt inventory mismatch")
    if not all(valid_sha(value) for value in list(inputs.values()) + list(outputs.values())):
        raise ValueError("Unknown actual artifact identity")
    for field in ["toolchain_identity_sha256", "build_log_sha256", "session_log_sha256", "wrapper_sha256"]:
        if not valid_sha(receipt.get(field)):
            raise ValueError("Missing live evidence: " + field)
    if receipt.get("dex2oat_sha256") != "ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b" or receipt.get("driver_sha256") != "14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46":
        raise ValueError("Frozen tool mismatch")
    if any(receipt.get(field) != 0 for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code"]):
        raise ValueError("Compiler or live logging failed")
    if receipt.get("status") != "verified" or not receipt.get("build_command") or not receipt.get("actual_argv"):
        raise ValueError("Missing actual execution")
    if receipt.get("exception_used") and not receipt.get("u14_outer_exception_approval"):
        raise ValueError("New image exception requires outer approval")


def check_review(records, review):
    if not records or any(not isinstance(row.get("exit_code"), int) for row in records):
        raise ValueError("Raw exit codes required")
    if review.get("applied") is not False or review.get("approved_by") is not None:
        raise ValueError("Review preview cannot become approval")
