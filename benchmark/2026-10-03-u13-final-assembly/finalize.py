import json
import shutil

from common import BASE, HERE, HOST, JAR, MASTER, PACKAGE, PREVIOUS, REPO, WS, portable, save, sha
import generation_bundle as bundle_tool
import generation_static_checks as static
import u7_executor as executor


def main():
    bundle, manifest, _ = bundle_tool.validate(PACKAGE)
    composition = json.loads((HERE / "composition.json").read_text())
    if sha(PACKAGE / "bundle.json") != composition["bundle_sha256"]:
        raise ValueError("Final bundle not frozen")
    shutil.copyfile(MASTER / "benchmark/2026-10-03-u13-gate-review/outer-approval.json", HERE / "evidence/outer-approval-final.json")
    plan = executor.prepare(PACKAGE, BASE / "native")
    save("evidence/offline-transaction-plan.json", plan)
    for board in composition["candidate_boards"].values():
        for target, digest in plan["expected"].items():
            if board["expected"].get(target) != digest:
                raise ValueError("Board composition disagrees with effective package: " + target)
    if manifest["files"]["payload/runtime/appspawn-x"] != HOST:
        raise ValueError("Host drift")
    if sha(PACKAGE / "framework/oh-adapter-runtime.jar") != JAR or sha(PACKAGE / "native/payload/android/framework/oh-adapter-runtime.jar") != JAR:
        raise ValueError("JAR copies not atomic")
    prior_manifest = json.loads((PREVIOUS / ".artifacts/bundle-v2/native/package.json").read_text())
    native_changes = {name for name, digest in manifest["files"].items() if prior_manifest["files"].get(name) != digest}
    if native_changes != {"payload/android/framework/oh-adapter-runtime.jar"}:
        raise ValueError("Unexpected native byte change after approval")
    tools = [MASTER / "scripts/lab" / name for name in ["u7_executor.py", "generation_bundle.py", "generation_static_checks.py",
        "open_site_scan.py", "deployed_class_diff.py", "deployed_strings_diff.py", "native_predeploy.py", "native_gate_common.py",
        "native_initialization_gate.py", "native_needed_gate.py", "deployment_native_gate.py", "auto_approve_exceptions.py", "oatdump_remote.sh"]]
    save("tool-provenance.json", dict(files=[dict(path=path, sha256=sha(path)) for path in tools],
        active_registry_sha256=sha(MASTER / "knowledge/gates/native-predeploy-exceptions.json"),
        final_approval_sha256=sha(MASTER / "benchmark/2026-10-03-u13-gate-review/outer-approval.json")))
    gate_results = {surface: json.loads((HERE / "gates" / (surface + ".json")).read_text()) for surface in ["mac", "vm"]}
    production_green = all(result.get("production_gates_passed") is True for result in gate_results.values())
    receipts = []
    if production_green:
        for surface, result in gate_results.items():
            if (result["actual_os"], result["architecture"]) != {"mac": ("Darwin", "arm64"), "vm": ("Linux", "x86_64")}[surface]:
                raise ValueError("Actual surface identity not proven")
            if (result["bundle_sha256"], result["native_manifest_sha256"], result["native_inputs_sha256"]) != (
                composition["bundle_sha256"], composition["native_manifest_sha256"], composition["native_inputs_sha256"]):
                raise ValueError("Production receipt bound to another package")
            if result["composed_frozen_violations"] != 0 or result.get("device_access") is not False:
                raise ValueError("Frozen/device scope changed")
            for record in result["records"] + [result["production"]]:
                raw_path = record["raw"].replace("$WORKSPACES", str(WS)).replace("$REPO", str(REPO))
                if record["exit_code"] != 0 or sha(raw_path) != record["raw_sha256"]:
                    raise ValueError("Missing, failed or mutated production command output")
            actual_plan = HERE / ".artifacts" / (surface + "-executor-plan.json")
            actual = json.loads(actual_plan.read_text())
            if actual.get("device_io") is not False or actual.get("gates_passed") is not True or actual.get("deployable") is not False:
                raise ValueError("Production transaction scope changed")
            if actual["image_gates"]["G1"] is not True or actual["image_gates"]["G2"] is not True or actual["static_checks"]["status"] != "PASS":
                raise ValueError("Production checks not all passed")
            current_native = actual["native_tickets"][0]["report"]
            if current_native["status"] != "PASS" or current_native["package_manifest_sha256"] != composition["native_manifest_sha256"] or current_native["inputs_sha256"] != composition["native_inputs_sha256"]:
                raise ValueError("Production native ticket not bound to final candidate")
            (HERE / "evidence" / (surface + "-executor-plan.json")).write_text(json.dumps(portable(actual), separators=(",", ":")) + "\n")
            replay = HERE / ".artifacts" / ("outer-replay-" + surface + ".txt")
            (HERE / "evidence" / ("outer-replay-" + surface + ".txt")).write_text(portable(replay.read_text()))
            receipts.append(dict(surface=surface, actual_plan=actual_plan, actual_plan_sha256=sha(actual_plan),
                outer_replay=replay, outer_replay_sha256=sha(replay), image_gates=actual["image_gates"],
                production_raw_sha256=result["production"]["raw_sha256"], verified_same_final_identity=True))
    save("production-receipts.json", dict(receipts=receipts, production_gates_passed=production_green, execution_enabled=False))
    save("results.json", dict(schema="u13-final-assembly/v1", bundle_sha256=composition["bundle_sha256"],
        package_manifest_sha256=composition["native_manifest_sha256"], inputs_sha256=composition["native_inputs_sha256"],
        runtime_jar_sha256=JAR, host_sha256=HOST, bundle_path=PACKAGE,
        approved_native_rows=159, unchanged_rebindings=157, new_resident_only_findings=2,
        old_to_new_issue_ids=json.loads((HERE / "registry-delta.json").read_text())["old_to_new_issue_ids"],
        static_status=json.loads((HERE / "evidence/static-v3-approved.json").read_text())["status"],
        native_status=json.loads((HERE / "evidence/native-v3-approved.json").read_text())["status"],
        production=gate_results, production_gates_passed=production_green, stage_a_authorized=False,
        execution_enabled=False, rollout_ready=False, device_access=False,
        blockers=[] if production_green else ["Actual fresh Mac and VM production gates must both pass before outer Phase A approval"],
        previous_bundle_unchanged=sha(PREVIOUS / ".artifacts/bundle-v2/bundle.json") == "adf3705043472de8797a677d76c16b5976cb9c0be11364daa3bbd1b882b1698b"))
    for name in ["hw248-readonly-probe", "vm-readonly-probe"]:
        raw = HERE / ".artifacts/raw" / (name + ".txt")
        (HERE / "evidence" / (name + ".txt")).write_text(portable(raw.read_text()))
    save("documentation.json", dict(readme_layout="| **`benchmark/2026-10-03-u13-final-assembly/`** | **Disabled U13 v3 with paired bbc3 JAR copies,159 signed rebindings, exact production delta/class allowances, and fresh Mac/VM admission receipts.** |",
        digest="U13 final: runtime JAR remains in native inventory although outside BCP; replacing it changes manifest/inputs/issue IDs. Production open delta includes even empty namespace fields; exact class allowances use the actual U12 baseline. Static approvals are not production or window PASS."))
    members = static.effective(PACKAGE)
    save("artifact-inventory.json", dict(files=[dict(target=target, source=row["source"], sha256=row["sha256"])
        for target, row in sorted(members.items())], manifest_sha256=sha(PACKAGE / "native/package.json"), device_access=False))
    paths = [str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file()
             and not any(part in {".artifacts", "__pycache__"} for part in path.relative_to(HERE).parts)
             and path.name != "landing-paths.txt"]
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u13-final-assembly").glob("*.md")]
    paths.append("tools/spec-checks/tests/u13_final_assembly.rs")
    paths.append("benchmark/2026-10-03-u13-final-assembly/landing-paths.txt")
    (HERE / "landing-paths.txt").write_text("\n".join(sorted(paths)) + "\n")
    print("FINAL_UNARMED bundle=" + composition["bundle_sha256"] + " production_green=" + str(production_green))


if __name__ == "__main__":
    main()
