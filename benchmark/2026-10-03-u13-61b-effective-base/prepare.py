import copy
import json
import shutil
import subprocess

from common import BASE, HERE, INSTALLS, MASTER, OLD_INSTALLS, ORIGINAL_BASE, ORIGINAL_BASE_SHA, ORIGINAL_PACKAGE, ORIGINAL_PACKAGE_SHA, PACKAGE, SERIAL, SOURCE, TARGETS, WS, save, sha
from validation import require_board_local_identity, require_exact_reference_delta
import generation_bundle as bundle
import u7_executor as executor


def write_reference(path, values):
    path.chmod(path.stat().st_mode | 0o200)
    path.write_text("\n".join(sorted(digest + "  " + target for target, digest in values.items())) + "\n")


def main():
    if sha(SOURCE) != INSTALLS or sha(ORIGINAL_BASE / "bundle.json") != ORIGINAL_BASE_SHA or sha(ORIGINAL_PACKAGE / "bundle.json") != ORIGINAL_PACKAGE_SHA:
        raise ValueError("Pinned original or source artifact changed; stop")
    if BASE.exists() or PACKAGE.exists():
        raise ValueError("Refuse to overwrite immutable variants")
    original_data, original_native, _ = bundle.validate(ORIGINAL_PACKAGE)
    base_data, base_native, _ = bundle.validate(ORIGINAL_BASE)
    if any(target in original_native[section] or target in base_native[section] for target in TARGETS for section in ["files", "live_hashes", "prerequisites"]):
        raise ValueError("Service is now in native inventory; reassess instead of borrowing reference-only fix")
    previous = json.loads((ORIGINAL_PACKAGE.parents[1] / "composition.json").read_text())
    signed = previous["baseline_boards"][SERIAL]
    target_state = previous["candidate_boards"][SERIAL]
    if any(signed["expected"][target] != INSTALLS or target_state["expected"][target] != INSTALLS for target in TARGETS):
        raise ValueError("Signed board does not preserve source51e1")
    if executor.fingerprints(signed["expected"], signed["reference_paths"]) != signed["fingerprints"]:
        raise ValueError("Signed baseline fingerprints inconsistent")
    BASE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", ORIGINAL_BASE, BASE], check=True)
    subprocess.run(["/bin/cp", "-cR", ORIGINAL_PACKAGE, PACKAGE], check=True)
    service_members = []
    for target in TARGETS:
        source = "native/board-local" + target
        path = BASE / source
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE, path)
        service_members.append(dict(source=source, target=target, sha256=sha(path)))
    changed_base = copy.deepcopy(base_data)
    base_reference = changed_base["reference"]["runtime"]
    values = bundle.read_fingerprint(BASE / base_reference["source"])
    values.update({target: INSTALLS for target in TARGETS})
    write_reference(BASE / base_reference["source"], values)
    base_reference["sha256"] = sha(BASE / base_reference["source"])
    changed_base["board_local_baseline"] = dict(serial=SERIAL, members=service_members, source_sha256=INSTALLS,
        semantics="Evidence-only existing board service; not a native mount, payload, installer upgrade or optional addition")
    save(BASE / "bundle.json", changed_base)
    base_sha = sha(BASE / "bundle.json")
    variant = copy.deepcopy(original_data)
    reference = variant["reference"]["runtime"]
    reference_path = PACKAGE / reference["source"]
    before = bundle.read_fingerprint(reference_path)
    after = dict(before)
    after.update({target: INSTALLS for target in TARGETS})
    require_exact_reference_delta(before, after, TARGETS, OLD_INSTALLS, INSTALLS)
    write_reference(reference_path, after)
    reference["sha256"] = sha(reference_path)
    variant["static_checks"]["baseline_bundle_sha256"] = base_sha
    variant["image_gate_reference"]["baseline_bundle_sha256"] = base_sha
    variant["transaction_scope_serial"] = SERIAL
    save(PACKAGE / "bundle.json", variant)
    metadata_path = PACKAGE / "expected-per-board.json"
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text())
        if SERIAL in metadata:
            for target in TARGETS:
                metadata[SERIAL]["expected"][target] = INSTALLS
            metadata_path.chmod(metadata_path.stat().st_mode | 0o200)
            save(metadata_path, metadata)
    bundle.validate(BASE)
    bundle.validate(PACKAGE)
    for original, variant_root in [(ORIGINAL_BASE, BASE), (ORIGINAL_PACKAGE, PACKAGE)]:
        for name in ["native/package.json", "native/native-checks/native-gates.json"]:
            if sha(original / name) != sha(variant_root / name):
                raise ValueError("Native manifest/inputs changed")
    plan = executor.prepare(PACKAGE, BASE / "native")
    require_board_local_identity(plan["baseline"], plan["expected"], TARGETS, INSTALLS, {row["target"] for row in plan["changes"]})
    if plan["baseline"] != signed["expected"] or plan["expected"] != target_state["expected"]:
        raise ValueError("Full 61b expected maps disagree with signed 316/319 identities")
    save("transaction-plan.json", plan)
    save("composition.json", dict(base=BASE, package=PACKAGE, serial=SERIAL, base_bundle_sha256=base_sha,
        original_base_bundle_sha256=ORIGINAL_BASE_SHA, original_package_bundle_sha256=ORIGINAL_PACKAGE_SHA,
        bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"),
        native_inputs_sha256=sha(PACKAGE / "native/native-checks/native-gates.json"), base_native_manifest_sha256=sha(BASE / "native/package.json"),
        base_native_inputs_sha256=sha(BASE / "native/native-checks/native-gates.json"), source=SOURCE, source_sha256=INSTALLS,
        board_local_members=service_members, baseline=signed, candidate=target_state, reference_changed_targets=TARGETS,
        output_bytes_changed=False, native_manifest_changed=False, original_package_unchanged=True,
        execution_enabled=False, device_access=False, production_status="PENDING_OUTER_REPLAY_AND_AUTHORIZATION"))
    for name, source in [("base-bundle.json", BASE / "bundle.json"), ("candidate-bundle.json", PACKAGE / "bundle.json"),
        ("native-manifest.json", PACKAGE / "native/package.json"), ("native-inputs.json", PACKAGE / "native/native-checks/native-gates.json")]:
        path = HERE / "manifests" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, path)
    mismatch = WS / "westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan/window1/61b-executor-baseline-mismatch.json"
    save("evidence/executor-refusal.json", json.loads(mismatch.read_text()))
    save("evidence/source-lineage.json", json.loads((WS / "westlake-harness-bms/benchmark/2026-10-02-libinstalls-unification/artifacts.json").read_text()), compact=True)
    save("critical-result.json", dict(baseline_full_identity=True, candidate_full_identity=True,
        baseline_paths=len(plan["baseline"]), candidate_paths=len(plan["expected"]), additions=len(plan["additions"]), changes=len(plan["changes"]),
        service_actions=[], service_baseline_expected=[dict(target=target, baseline=plan["baseline"][target], expected=plan["expected"][target]) for target in TARGETS],
        baseline_fingerprints=executor.fingerprints(plan["baseline"], signed["reference_paths"]),
        source_found=True, source_sha256=sha(SOURCE), rebuilt=False, deployment=False))
    if sha(ORIGINAL_PACKAGE / "bundle.json") != ORIGINAL_PACKAGE_SHA:
        raise ValueError("Authorized original changed")
    print("BASE61b=" + base_sha + " U13_METADATA61b=" + sha(PACKAGE / "bundle.json"))
    print("FULL_IDENTITY baseline316/candidate319 exact signed maps; additions3/changes40; two service aliases51e1 unchanged, no service action")
    print("Native85aef68e/inputs c40faa79 and all outputs preserved; original91272eaf unchanged; replay/authorization pending")


if __name__ == "__main__":
    main()
