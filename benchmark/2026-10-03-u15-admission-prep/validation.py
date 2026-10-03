import hashlib
import json
import re


FLUTTER = "9b8245022f9c98dac41a85acfa553e96e6385073fd7b15298199a1cce223647b"
HOST = "9e3ad72e1ff5de52435ce2ca91eacf5346f18aaadcdb96824b6713f3f849de09"
ANL = "b96a8991ef5a2a6e800029aed968b2442f50786466ac2a1a19979959b56d8bbc"
MANIFEST = "ce64197956baea7b8a96601601480665f6cbec492cbe77f67ec46181a7422d7e"
INPUTS = "58eb84fc1684fa6b13c4f0305151bd665c3cf444cd9d0aba444730bbf261fd37"
COMPILER = "ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b"
DRIVER = "14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46"
READONLY_STRINGS_SHA = "b6b466d7ac5dc65b5ee50fd5ee96e0c395f816b496949613659c0ddac572bde9"
FIELDS = ["actual_argv", "argv_sha256", "toolchain_identity_sha256", "hostlibs_sha256", "build_log_sha256",
    "session_log_sha256", "dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code", "frozen_driver_exit_code"]


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def check_atomic(files):
    required = {"payload/runtime/appspawn-x": HOST, "payload/android/lib64/libapp_native_loader.so": ANL,
        "payload/route/libapp_native_loader.so": ANL, "payload/android/lib64/westlake_flutter/libandroid.so": FLUTTER}
    if any(files.get(name) != digest for name, digest in required.items()):
        raise ValueError("Exact ANL/host atomic pair and Flutter private slot required")


def check_preview(preview, mapping):
    rows = preview["exceptions"]
    if preview["applied"] or preview["execution_enabled"] or preview["final_binding_ready"]:
        raise ValueError("Preview cannot be applied or final")
    if preview["final_manifest_sha256"] is not None or preview["final_inputs_sha256"] is not None:
        raise ValueError("Final hashes are unknown before complete composition")
    if len(rows) != 204 or len(mapping) != 204 or len({row["issue_id"] for row in rows}) != 204:
        raise ValueError("Exactly 204 unique mappings required")
    if {gate: sum(row["gate"] == gate for row in rows) for gate in ["N1", "N2"]} != {"N1": 99, "N2": 105}:
        raise ValueError("N1/N2 count drift")
    indexed = {row["issue_id"]: row for row in rows}
    for row in mapping:
        target = indexed[row["partial_issue_id"]]
        if target["package_manifest_sha256"] != MANIFEST or target["inputs_sha256"] != INPUTS:
            raise ValueError("Partial binding drift")
        if target["auto_from"]["issue_id"] != row["old_issue_id"] or row["final_issue_id"] is not None:
            raise ValueError("Mapping must retain source and unknown final identity")
        if row["semantic_sha256"] != row["baseline_semantic_sha256"]:
            raise ValueError("Finding semantics changed")


def check_admission(decision):
    if not decision["target_present_in_baseline"] or decision["candidate_sha256"] != FLUTTER:
        raise ValueError("Flutter must be an exact replacement in this content comparison")
    if decision["new_native_row_required"] or decision["admissions"] or decision["applied"]:
        raise ValueError("No new-native row for existing Flutter target")


def check_pair_template(pair, inputs, images):
    if pair["status"] != "NOT_RUN" or pair["selected_run"] is not None or pair["deploy_allowed"]:
        raise ValueError("Template is not executed or selected")
    if len(inputs) != 9 or len(images) != 27 or [row["run"] for row in pair["runs"]] != [1, 2]:
        raise ValueError("Two complete runs required")
    for row in pair["runs"]:
        if row["input_jars"] != inputs or set(row["outputs"]) != set(images):
            raise ValueError("Template input/output identity map incomplete")
        if any(value is not None for value in row["outputs"].values()) or any(row[field] is not None for field in FIELDS):
            raise ValueError("No actual build evidence may be fabricated")
        if row["exception_used"] or row["u15_outer_exception_approval"] is not None:
            raise ValueError("Historical image exception cannot be copied")


def check_actual_pair(pair, inputs, images):
    if pair.get("status") != "verified" or len(pair.get("runs", [])) != 2:
        raise ValueError("Actual paired evidence required")
    for row in pair["runs"]:
        if row.get("input_jars") != inputs or set(row.get("outputs", {})) != set(images):
            raise ValueError("Actual receipt inventory incomplete")
        if not all(valid_sha(value) for value in row["outputs"].values()):
            raise ValueError("Actual output hashes required")
        if row.get("dex2oat_sha256") != COMPILER or row.get("driver_sha256") != DRIVER:
            raise ValueError("Frozen compiler or driver drift")
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            if type(row.get(field)) is not int or row[field] != 0:
                raise ValueError("Failed compiler or live logging")
        if type(row.get("frozen_driver_exit_code")) is not int or row["frozen_driver_exit_code"] not in [0, 6]:
            raise ValueError("Frozen driver status missing or failed")
        for field in ["argv_sha256", "toolchain_identity_sha256", "hostlibs_sha256", "build_log_sha256", "session_log_sha256"]:
            if not valid_sha(row.get(field)):
                raise ValueError("Actual evidence hash missing")
        argv = row.get("actual_argv")
        if not isinstance(argv, list) or not argv or hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest() != row["argv_sha256"]:
            raise ValueError("Actual argv does not match its canonical hash")
        if row.get("exception_used"):
            approval = row.get("u15_outer_exception_approval") or {}
            if approval.get("input_jars") != inputs or approval.get("outputs") != row["outputs"] or not valid_sha(approval.get("sha256")):
                raise ValueError("New exact input/output approval required; historical exception rejected")
    first, second = pair["runs"]
    if first["run"] != 1 or second["run"] != 2 or first["actual_argv"] != second["actual_argv"] or first["hostlibs_sha256"] != second["hostlibs_sha256"]:
        raise ValueError("Paired argv or host library inventory mismatch")
