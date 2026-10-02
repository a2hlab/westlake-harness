import json
from pathlib import Path
import subprocess
import sys
import tempfile

from finalize import HERE, MASTER, REPO, save, sha
from reports import capture, expand
from validation import ABI_TARGET, INSTALLER_PATHS, check_local_plan
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def main():
    signed_path = HERE / "registry-delta-signed.json"
    signed = json.loads(signed_path.read_text())
    approval = json.loads((MASTER / "benchmark/2026-10-03-u14-review/outer-approval-findings.json").read_text())
    for row in signed["old_to_new"]:
        row.update(approved_by=approval["signer"], approved_at=approval["signed_at"], transferred=True)
    old = json.loads((HERE.parent / "2026-10-03-u14-final-assembly/needs-outer-review.json").read_text())
    signed.update(old_manifest_sha256=old["package_manifest_sha256"], old_inputs_sha256=old["inputs_sha256"],
        new_manifest_sha256=signed["exceptions"][0]["package_manifest_sha256"], new_inputs_sha256=signed["exceptions"][0]["inputs_sha256"])
    save(signed_path, signed)
    variants = {}
    byte_maps = []
    for variant in ["common", "61b"]:
        root = HERE / variant
        composition = json.loads((root / "reviewed-composition.json").read_text())
        package = expand(composition["package"])
        baseline = expand(composition["transaction_base"])
        if sha(package / "bundle.json") != composition["bundle_sha256"]:
            raise ValueError("Reviewed package binding drift")
        data, _, _ = bundle_tool.validate(package)
        if data.get("rollout_ready"):
            raise ValueError("Reviewed package no longer disabled")
        byte_maps.append({target: row["sha256"] for target, row in static.effective(package).items()})
        plan = executor.prepare(package, baseline / "native")
        check_local_plan(plan, composition["baseline"])
        save(root / "reviewed-transaction-plan.json", plan)
        diagnostic = json.loads((HERE / (variant + "-diagnostic") / "composition.json").read_text())
        diagnostic["identity_role"] = "signed-t8-reference-diagnostic-only"
        save(HERE / (variant + "-diagnostic") / "composition.json", diagnostic)
        diagnostics = dict(composition=diagnostic, status="EXPECTED-REJECT-BASE-NOT-PROMOTED",
            unapproved_host_delta_sha256="c818ed550cf34f22c4dd4528153afc61e896a5b4408e8935441221f883ab7ddb",
            classification="Expected diagnostic refusal because the real T8 base is not promoted U13; outer 2026-10-03 06:32 explicitly declined an exception", exception_created=False,
            production_replay="outer only after current window", other_unsigned_t8_increments="Raw preview retained; conditional U13 policy is not silently used for different byte pairs")
        save(HERE / (variant + "-diagnostic") / "results.json", diagnostics)
        variants[variant] = dict(terminal=composition, diagnostic=diagnostics,
            artifact_gates=json.loads((root / "artifact-gates-reviewed.json").read_text()),
            baseline_installer={target: plan["baseline"][target] for target in INSTALLER_PATHS},
            expected_installer={target: plan["expected"][target] for target in INSTALLER_PATHS}, installer_operations=0)
    if byte_maps[0] != byte_maps[1]:
        raise ValueError("Per-board variants have different candidate artifacts")
    if byte_maps[0][ABI_TARGET] != "f8619ad5571c92cb3e9da3b8265ee41c17fa67db0a6aabeb9bfb89903e2a2239":
        raise ValueError("Final ABI slot changed")
    save(HERE / "results.json", dict(variants=variants, signed_exception_rows=204, signed_new_rows=45, old_rebind_rows=159,
        identical_candidate_artifacts=True, production_mac="pending-outer-replay", production_vm="pending-outer-replay",
        promotion_confirmed=False, execution_enabled=False, active_registries_updated=False, vm_used=False, device_access=False,
        image_reproduction="approved-exact-new-pair", predicted_first_fatal_movement=2, board_verified_movement=0))
    records = [capture(HERE, "tests-rust", ["cargo", "test", "--manifest-path", REPO / "tools/spec-checks/Cargo.toml", "--test", "u14_effective_rebind"])]
    if records[0]["exit_code"]:
        raise ValueError("Rust tests failed")
    listed = sorted(path.relative_to(REPO).as_posix() for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts and "__pycache__" not in path.parts and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    listed += ["specs/u14-effective-rebind/project.spec.md", "specs/u14-effective-rebind/t1-bind.spec.md", "tools/spec-checks/tests/u14_effective_rebind.rs"]
    with tempfile.TemporaryDirectory(prefix="u14-rebind-cold-") as temporary:
        root = Path(temporary)
        for name in listed:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((REPO / name).read_bytes())
        record = capture(HERE, "tests-cold", [sys.executable, root / HERE.relative_to(REPO) / "test_binding.py"])
        if record["exit_code"]:
            raise ValueError("Cold public-only tests failed")
        records.append(record)
    save(HERE / "test-summary.json", dict(python_tests=11, rust_selectors=2, cold_private_artifacts=False, records=records))
    for name in ["test-summary.json", "evidence/tests-cold.txt", "evidence/preflight.txt", "listing-receipt.json"]:
        listed.append((HERE / name).relative_to(REPO).as_posix())
    preflight = HERE / "evidence/preflight.txt"
    if not preflight.exists():
        preflight.write_text("Preflight not yet executed\n")
    listing = HERE / "landing-paths.txt"
    listing.write_text("\n".join(sorted(set(listed))) + "\n")
    save(HERE / "listing-receipt.json", dict(listing_sha256=sha(listing), paths=len(set(listed)),
        files=[dict(path=name, sha256=sha(REPO / name), bytes=(REPO / name).stat().st_size) for name in sorted(set(listed)) if not name.endswith("/listing-receipt.json")], git_index_write=False))
    print("LANDING paths=" + str(len(set(listed))) + " sha=" + sha(listing))


if __name__ == "__main__":
    main()
