import json
from pathlib import Path

from build_window_shim import digest


HERE = Path(__file__).resolve().parent
MISSING_INLINE = "_ZN7_JNIEnv16CallObjectMethodEP8_jobjectP10_jmethodIDz"


def check():
    report = json.loads((HERE / "evidence/consumers.json").read_text())
    receipt = json.loads((HERE / "evidence/build-receipt.json").read_text())
    payload = json.loads((HERE / "evidence/payload-inline-consumers.json").read_text())
    approval = json.loads((HERE / "evidence/export-exception.json").read_text())
    errors = []
    if report["candidate_sha256"] != receipt["candidate_sha256"]:
        errors.append("candidate receipt mismatch")
    if report["union_owner_consumer_breaks"]:
        errors.append("APK owner-union consumer break")
    if report["missing_superset_exports"] != [MISSING_INLINE] or approval["symbol"] != MISSING_INLINE:
        errors.append("unexpected missing export or exception symbol")
    if approval["payload_evidence_sha256"] != digest(HERE / "evidence/payload-inline-consumers.json"):
        errors.append("payload exception evidence changed")
    if not payload["condition_passed"] or payload["missing_inline_consumers"] or report["missing_inline_consumers_all_APK_members"]:
        errors.append("conditional exception consumer exists")
    if approval["decision"] != "approved conditional; satisfied for inspected manifest":
        errors.append("outer exception not approved")
    return {"schema": "u11-window-offline-gate-v1", "passed": not errors, "errors": errors,
            "candidate_sha256": receipt["candidate_sha256"],
            "export_superset": "267 covered + exactly one outer-approved zero-consumer exception",
            "exception_manifest_sha256": payload["manifest_sha256"],
            "canonical_flat_abi_failure_retained": True,
            "scope": "offline source/consumer acceptance only; exception must be rerun on final U11 payload",
            "release_gate": "pending: same-generation assembly, target namespace/single-owner maps and screenshot controls",
            "deploy_authorized": False}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
