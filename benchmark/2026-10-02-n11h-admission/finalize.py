import json
from pathlib import Path
import shutil

from settings import ACCEPTED, BASE_SHA, HERE, HOST_SHA, INPUTS_SHA, MANIFEST_SHA, MASTER, REPO, candidate_report, file, load, reference, save, sha


def portable(text):
    replacements = [(str(REPO), "$REPO"), (str(MASTER), "$WORKSPACES/westlake-harness"),
                    (str(REPO.parent), "$WORKSPACES")]
    for original, displayed in replacements:
        text = text.replace(original, displayed)
    return text


def main():
    raw = HERE / ".artifacts/raw-outputs"
    raw.mkdir(parents=True, exist_ok=True)
    receipts = []
    final_names = {"cargo.txt": "cargo-final.txt", "t1-lifecycle.json": "t1-final.json", "t2-lifecycle.json": "t2-final.json",
                   "t1-lifecycle-stderr.txt": "t1-final-stderr.txt", "t2-lifecycle-stderr.txt": "t2-final-stderr.txt"}
    final_run = any((raw / name).exists() for name in final_names.values())
    if final_run and not all((raw / name).is_file() for name in final_names.values()):
        raise ValueError("incomplete final raw run")
    for name in ["cargo.txt", "t1-lifecycle.json", "t2-lifecycle.json", "t1-lifecycle-stderr.txt", "t2-lifecycle-stderr.txt"]:
        path = HERE / "evidence" / name
        archive = raw / (final_names[name] if final_run else name)
        if not archive.exists():
            shutil.copyfile(path, archive)
        if path.suffix == ".json":
            transformed = portable(archive.read_text())
            json.loads(transformed)
            path.write_text(transformed)
        else:
            path.write_text(portable(archive.read_text()))
        receipts.append(dict(path="evidence/" + name, raw_path="$WORKSPACES/westlake-harness-bms/" +
                             str(archive.relative_to(REPO)), raw_sha256=sha(archive), published_sha256=sha(path),
                             transformation="Exact repository/workspaces path-prefix replacement only; raw original retained"))
    save(HERE / "evidence/raw-outputs.json", receipts)
    scenarios = []
    for name in ["t1", "t2"]:
        result = json.loads((HERE / "evidence" / (name + "-lifecycle.json")).read_text())
        if not result["passed"] or result["verification"]["summary"]["passed"] != 2:
            raise ValueError("contract failed")
        for scenario in result["verification"]["results"]:
            evidence = scenario["evidence"]
            outputs = [row for row in evidence if row.get("type") == "test_output"]
            if len(outputs) != 1 or "1 passed; 0 failed" not in outputs[0]["stdout"]:
                raise ValueError("selector did not run a passing Rust test")
            scenarios.append(dict(contract=name, scenario=scenario["scenario_name"], verdict=scenario["verdict"],
                                  selector=outputs[0]["test_name"], selected_test_pass=True))
    save(HERE / "evidence/test-selection.json", scenarios)
    witnesses = [reference(ACCEPTED + "/inputs/host-r3.c", "if (U10ShareResidentCompat(&compat_owner) == 0"),
                 reference(ACCEPTED + "/src/candidate-stock-host.c", "const bool compat_ready"),
                 reference(ACCEPTED + "/src/candidate-stock-host.c", "const char *owner_shared"),
                 reference(ACCEPTED + "/inputs/resident-compat.h", "unavailable missing"),
                 reference(ACCEPTED + "/inputs/resident-compat.h", "unavailable unmapped"),
                 reference(ACCEPTED + "/inputs/resident-compat.h", "unavailable result="),
                 reference(ACCEPTED + "/inputs/resident-compat.h", "owner_verified view="),
                 reference(ACCEPTED + "/src/candidate-stock-host.c", "unavailable inherit result=")]
    save(HERE / "evidence/timing-source-witnesses.json", witnesses)
    evidence_paths = set()
    for name in ["registry-delta.json", "n1-existing-registry-delta.json"]:
        for entry in json.loads((HERE / name).read_text())["exceptions"]:
            evidence_paths.update(entry["evidence"])
    evidence_paths.update(json.loads((HERE / "outer-review.json").read_text())["evidence"])
    save(HERE / "evidence/existing-paths.json", [dict(path=name, sha256=sha(file(name))) for name in sorted(evidence_paths)])
    report = candidate_report()
    save(HERE / "results.json", dict(schema_version=1, device_access=False, accepted_candidate_modified=False,
         live_registry_modified=False, window_authorized=False, state="PENDING_OUTER_ADMISSION_REVIEW",
         baseline_host_sha256=BASE_SHA, candidate_host_sha256=HOST_SHA, package_manifest_sha256=MANIFEST_SHA,
         inputs_sha256=INPUTS_SHA, compat=dict(zero_behavior_delta=False, late_mapping="r3 verified / N11h unavailable; simulated platform",
         private_delta="r3 helper evaluated before private guards; N11h helper skipped", unavailable_is_success=False,
         unavailable_alone_is_smoke_failure=False, readout="knowledge/smoke/n11h-compat-readout.json"),
         strings=dict(dropped=3, added=16, outer_checked=0, state="PENDING"),
         exceptions=dict(N2_auto_identical_proposed=103, existing_N1_separate_proposed=53, new_N1_pending=1,
                         raw_candidate_status=report["status"], simulated_combined_status="REJECT", full_gate_pass=False),
         validation=dict(python_tests=19, rust_selectors=4, skipped=0, contract_scenarios=scenarios)))
    print("finalize: accepted bytes/bindings unchanged; raw outputs retained; four selectors ran 1 test each")
    print("admission: PENDING_OUTER_REVIEW; simulated complete native gate remains REJECT")


if __name__ == "__main__":
    main()
