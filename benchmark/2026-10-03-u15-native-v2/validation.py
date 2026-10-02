import re

RUNTIME = "94c31177709dbea0b1615a63c0d41a358f7db6843cbbd11f77979576a1a86a47"
HOST = "9e3ad72e1ff5de52435ce2ca91eacf5346f18aaadcdb96824b6713f3f849de09"
ANL = "b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc"
HOST_SOURCE = "63e2d25a6c383cd886b57b3b0220da03b6f0139bbbfba208a7165b272cc17217"
FLUTTER = "9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b"
CHANGES = {
    "payload/android/lib64/westlake_flutter/libandroid.so": FLUTTER,
    "payload/android/lib64/liboh_android_runtime.so": RUNTIME,
    "payload/runtime/appspawn-x": HOST,
    "payload/android/lib64/libapp_native_loader.so": ANL,
    "payload/route/libapp_native_loader.so": ANL,
}
BASES = {
    "common": "9b42ddc6324c63e13d494a8e1144b3c196e70dabeb5ca7a8ec4fc36b58961cd1",
    "61b": "f589844793299c3884a6738b2a4168dffe45680e89379cd53774bbde5c42835e",
}


def check_partial(old, new, state, descriptor_exists=False):
    changes = {name: digest for name, digest in new.items() if name in old and old[name] != digest}
    if changes != CHANGES or set(old) != set(new):
        raise ValueError("Exactly five payload replacements required, with both ANL aliases")
    if descriptor_exists or any(state.get(field) is not False for field in ["execution_enabled", "final_batch_complete", "deploy_allowed", "promotion_confirmed"]):
        raise ValueError("Native-only draft cannot claim execution or promotion")
    if state.get("paired_receipt") is not None or state.get("images") != "pending framework+NSD single rebake":
        raise ValueError("Historical images cannot attest a new U15 pair")
    if state.get("transaction_base") != {"common": None, "61b": None}:
        raise ValueError("Transaction base is a future signed per-board parameter")


def packages(source):
    matched = re.search(r"static bool native_cluster_path\([^)]*\)\s*\{\s*const char\* packages\[\]\s*=\s*\{([^}]+)\}", source)
    if not matched:
        raise ValueError("Native package list not resolved")
    return re.findall(r'"([^"]+)"', matched.group(1))


def check_routes(anl, host):
    first, second = packages(anl), packages(host)
    if first != second or first.count("org.jitsi.meet") != 1:
        raise ValueError("ANL and host native-domain lists must match including Meet once")
    runtime = re.search(r"const bool needs_runtime\s*=([\s\S]+?);", host)
    if not runtime or '"/org.jitsi.meet/"' not in runtime.group(1):
        raise ValueError("Meet resident-runtime publication is missing")
    return first


def check_review(report):
    if not report.get("records") or any(not isinstance(row.get("exit_code"), int) or not row.get("raw_sha256") for row in report["records"]):
        raise ValueError("Hash-bound raw return codes required")
    if report.get("approvals_applied") is not False or report.get("active_registry_updated") is not False or report.get("execution_enabled") is not False:
        raise ValueError("Review preview cannot become approval")
    if report.get("production_run") is not False or report.get("image_bake_run") is not False:
        raise ValueError("Historical PASS cannot substitute for pending production/images")
