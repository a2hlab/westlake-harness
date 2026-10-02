import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE_PREFIX = "benchmark/2026-10-03-u13-gate-review/"
RUNTIME = "18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae"
COMPAT = "b8a87f6fe2902b1d1c9e8440714d32dbdfd05d75dc1a2993fd2624af91d15abc"
BASE_COMPAT = "015aa3a632eabe057bd8d6ce0e0ff181209da7dcab8de22409a79addc0a56d58"
DELTA = "2cd13b3defeda8318d91d23d1ab8e63f77b0bb79e45bc5961f27fa67e864bd3d"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def draft_native_rows(report, manifest_bytes, inputs_bytes, evidence_path):
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    inputs_sha = hashlib.sha256(inputs_bytes).hexdigest()
    if (report["package_manifest_sha256"], report["inputs_sha256"]) != (manifest_sha, inputs_sha):
        raise ValueError("Stale report: rerun native_predeploy against exact final package and inputs")
    manifest = json.loads(manifest_bytes)
    if manifest["files"]["payload/android/lib64/liboh_android_runtime.so"] != RUNTIME:
        raise ValueError("Changed runtime requires new source/binary review, not hash-only rebinding")
    if manifest["files"]["payload/android/lib64/libbionic_compat.so"] != COMPAT:
        raise ValueError("Changed compat requires new review")
    if Path(evidence_path).is_absolute() or ".." in Path(evidence_path).parts:
        raise ValueError("Evidence must be an existing landed repository-relative report")
    if not (HERE.parents[1] / evidence_path).is_file():
        raise ValueError("Evidence path does not exist")
    known = {"resolve_oh_wm_funcs": ("liboh_adapter_bridge.so", 415),
             "eglCreateWindowSurface": ("libEGL.so", 1408)}
    rows = []
    for source in report["gates"]["N1"]["findings"]:
        if source.get("profile") != "u13-m1-compat-shim.cpp":
            continue
        detail = source["detail"]
        if detail["function"] not in known:
            raise ValueError("New full-gfx finding requires fresh review")
        library, line = known[detail["function"]]
        if detail["library"] != library or detail["evidence"]["line"] != line or "RTLD_NOLOAD" not in detail["evidence"]["text"]:
            raise ValueError("Finding source/target changed")
        finding = {key: value for key, value in source.items() if key not in {"issue_id", "disposition", "exception", "gate"}}
        issue_id = digest(dict(gate="N1", package_manifest_sha256=manifest_sha, inputs_sha256=inputs_sha, finding=finding))
        if issue_id != source["issue_id"]:
            raise ValueError("Finding ID mismatch; do not string-replace previous IDs")
        rows.append(dict(gate="N1", package_manifest_sha256=manifest_sha, inputs_sha256=inputs_sha,
            issue_id=issue_id, reason="Existing resident-only " + library + " lookup is newly covered by full-gfx N1; old source and old/new ELF retain NOW|NOLOAD. A miss fails closed without a fresh fallback; this is not proof of resident availability or correct single owner.",
            removal_condition="Remove after complete resident owner/namespace/timing proof or a verified fix. Any manifest, inputs, source, runtime, finding or owner drift requires new review.",
            evidence=[evidence_path, EVIDENCE_PREFIX + "lineage.json", EVIDENCE_PREFIX + "evidence/source-lines.json",
                      EVIDENCE_PREFIX + "evidence/noload-flags.json"], approved_by=None, approved_at=None))
    if len(rows) != 2:
        raise ValueError("Expected exactly two full-gfx N1 review findings")
    return dict(schema_version=1, exceptions=rows)


def draft_static_policy(review, manifest_sha):
    rows = {}
    for item in review["review_required"]:
        if (item["candidate_sha256"], item["deployed_sha256"], item["delta_sha256"]) != (COMPAT, BASE_COMPAT, DELTA):
            raise ValueError("Changed compatibility pair/delta requires new disassembly review")
        rows[item["target"]] = dict(candidate_sha256=COMPAT, deployed_sha256=BASE_COMPAT,
            delta_sha256=DELTA, package_manifest_sha256=manifest_sha,
            reason="Unchanged backend-call diagnostic PC moves3758->3a58 in VLC then3b98 after the one-data-export ctype rebind; full function branch/GOT/string semantics match in all three. Both same-byte compat aliases must share this review.",
            evidence=[EVIDENCE_PREFIX + "semantics.json", EVIDENCE_PREFIX + "evidence/dlext-old.txt",
                      EVIDENCE_PREFIX + "evidence/dlext-new.txt"], approved_by=None, approved_at=None)
    if len(rows) != 2:
        raise ValueError("Both root and route compat aliases are required")
    if not all(target == "/system/android/lib64/libbionic_compat.so" or target.startswith("/system/lib64/westlake/route-a/") and target.endswith("/libbionic_compat.so") for target in rows):
        raise ValueError("Unexpected compat target")
    return dict(native=rows, package_manifest_sha256=manifest_sha, execution_enabled=False,
                note="generation_static_checks checks the pair/delta/outer signer, not this extra manifest field; admission and wrapper must bind the final manifest/bundle separately")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--static-review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest_bytes = args.manifest.read_bytes()
    rows = draft_native_rows(json.loads(args.report.read_text()), manifest_bytes, args.inputs.read_bytes(), args.evidence_path)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "native-predeploy-exceptions.draft.json").write_text(json.dumps(rows, indent=2) + "\n")
    static = draft_static_policy(json.loads(args.static_review.read_text()), hashlib.sha256(manifest_bytes).hexdigest())
    (args.out / "static-policy.draft.json").write_text(json.dumps(static, indent=2) + "\n")
    print("DRAFT_ONLY: two N1 rows and two static aliases; no approval/registry/package change")


if __name__ == "__main__":
    main()
