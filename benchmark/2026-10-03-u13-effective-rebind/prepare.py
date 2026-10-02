import copy
import json
import shutil
import subprocess

from common import BASE, BASE_SHA, HERE, MASTER, OLD_SHA, PACKAGE, PREVIOUS, save, sha
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def main():
    old = PREVIOUS / ".artifacts/bundle-v3"
    if sha(BASE / "bundle.json") != BASE_SHA or sha(old / "bundle.json") != OLD_SHA:
        raise ValueError("Pinned base or candidate changed")
    if PACKAGE.exists():
        raise ValueError("Do not overwrite a frozen draft")
    old_bundle, old_manifest, _ = bundle_tool.validate(old)
    base_bundle, base_manifest, _ = bundle_tool.validate(BASE)
    recovery = json.loads((MASTER / "benchmark/2026-10-02-u12-final-assembly/recovery-u101t8.json").read_text())
    expected_fps = json.loads((MASTER / "benchmark/2026-10-02-u10-1-t8-rerun/composition.json").read_text())["expected_fingerprints"]
    candidate_boards = json.loads((PREVIOUS / "composition.json").read_text())["candidate_boards"]
    for serial, board in recovery["boards"].items():
        board["reference_paths"] = {kind: [target for target in paths if target in board["expected"]]
                                    for kind, paths in candidate_boards[serial]["reference_paths"].items()}
        if executor.fingerprints(board["expected"], board["reference_paths"]) != expected_fps[serial]:
            raise ValueError("Recovery snapshot does not match signed U10.1T8 fingerprints")
        if len(board["expected"]) != 316:
            raise ValueError("Recovery inventory must have 316 unique paths / 318 identity assertions")
        for target, row in static.effective(BASE).items():
            if board["expected"][target] != row["sha256"]:
                raise ValueError("Real baseline bundle / recovery disagreement: " + target)
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/bin/cp", "-cR", old, PACKAGE], check=True)
    selected = recovery["boards"][next(iter(recovery["boards"]))]
    reference_mapping = []
    bundle = copy.deepcopy(old_bundle)
    for kind in ["runtime", "boot"]:
        entry = bundle["reference"][kind]
        path = PACKAGE / entry["source"]
        values = {target: selected["expected"][target] for target in selected["reference_paths"][kind]}
        path.chmod(path.stat().st_mode | 0o200)
        path.write_text("\n".join(sorted(value + "  " + target for target, value in values.items())) + "\n")
        reference_mapping.append(dict(kind=kind, old_sha256=entry["sha256"], new_sha256=sha(path), files=len(values)))
        entry["sha256"] = sha(path)
    effective_base = static.effective(BASE)
    image_mapping = []
    for entry in bundle["image_gate_reference"]["members"]:
        target = entry["target"]
        deployed = effective_base[target]
        destination = PACKAGE / entry["source"]
        destination.chmod(destination.stat().st_mode | 0o200)
        shutil.copyfile(bundle_tool.member(BASE, deployed), destination)
        image_mapping.append(dict(target=target, old_sha256=entry["sha256"], new_sha256=sha(destination)))
        entry["sha256"] = sha(destination)
    bundle["image_gate_reference"].update(kind="signed-effective-U10.1T8", baseline_bundle_sha256=BASE_SHA)
    bundle["static_checks"]["baseline_bundle_sha256"] = BASE_SHA
    bundle["rollout_ready"] = False
    bundle["rollout_blocker"] = "Real U10.1T8 rebind; fresh two-surface production and outer authorization pending"
    save(PACKAGE / "bundle.json", bundle)
    _, candidate_manifest, _ = bundle_tool.validate(PACKAGE)
    if candidate_manifest != old_manifest or sha(PACKAGE / "native/native-checks/native-gates.json") != sha(old / "native/native-checks/native-gates.json"):
        raise ValueError("Rebinding must not change native payload/manifest/inputs")
    save("composition.json", dict(package=PACKAGE, base=BASE, base_bundle_sha256=BASE_SHA, previous_bundle_sha256=OLD_SHA,
        bundle_sha256=sha(PACKAGE / "bundle.json"), native_manifest_sha256=sha(PACKAGE / "native/package.json"),
        native_inputs_sha256=sha(PACKAGE / "native/native-checks/native-gates.json"),
        payload_changed_from_u13=[], boot_outputs_changed_from_u13=[], native_manifest_unchanged=True,
        baseline_boards=recovery["boards"], candidate_boards=candidate_boards,
        reference_mapping=reference_mapping, image_reference_mapping=image_mapping,
        execution_enabled=False, rollout_ready=False, production_status="PENDING_OUTER_FRESH_REPLAY"))
    plan = executor.prepare(PACKAGE, BASE / "native")
    save("transaction-plan.json", plan)
    save("evidence/base-composition.json", json.loads((MASTER / "benchmark/2026-10-02-u10-1-t8-rerun/composition.json").read_text()))
    print("REAL_BASE " + BASE_SHA + " new_bundle=" + sha(PACKAGE / "bundle.json"))
    print("transaction changes=" + str(len(plan["changes"])) + " additions=" + str(len(plan["additions"])) + " receipt=" + plan["build_receipt"]["status"])


if __name__ == "__main__":
    main()
