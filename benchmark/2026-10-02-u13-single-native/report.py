import datetime
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from build import HERE, HOST_SHA, MASTER, POLICY_SHA, REPO, U12, WS, portable, run, save, sha


def main():
    records = []
    for name in ["u12", "candidate"]:
        raw = HERE / ".artifacts/raw" / ("native-" + name + ".txt")
        save("evidence/native-" + name + ".json", json.loads(raw.read_text()))
    baseline = json.loads((HERE / "evidence/native-u12.json").read_text())
    candidate = json.loads((HERE / "evidence/native-candidate.json").read_text())
    spec = importlib.util.spec_from_file_location("approval", MASTER / "scripts/lab/auto_approve_exceptions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry = json.loads((MASTER / "knowledge/gates/native-predeploy-exceptions.json").read_text())
    matched, new = module.classify(candidate, [baseline], registry["exceptions"])
    rows = []
    prefix = HERE.relative_to(REPO).as_posix()
    for gate, finding, prior in matched:
        rows.append(dict(gate=gate, package_manifest_sha256=candidate["package_manifest_sha256"],
            inputs_sha256=candidate["inputs_sha256"], issue_id=finding["issue_id"],
            reason="Identical to approved finding " + prior["issue_id"] + "; delta generated for outer review, not applied to master.",
            removal_condition=prior["removal_condition"],
            evidence=[prefix + "/evidence/native-candidate.json", prefix + "/evidence/native-u12.json"],
            approved_by=module.AUTO, approved_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            auto_from=dict(package_manifest_sha256=prior["package_manifest_sha256"], issue_id=prior["issue_id"])))
    save("registry-delta.json", dict(exceptions=rows))
    save("outer-review.json", dict(new_findings=[dict(finding, gate=gate) for gate, finding, _ in new],
        applied=False, scope="Two-piece audit only. Final U13 runtime/compat composition requires a fresh manifest-bound gate."))
    for row in rows:
        for name in row["evidence"]:
            if not (REPO / name).is_file():
                raise ValueError("registry delta evidence does not exist")
    if new or len(matched) != 157:
        raise ValueError("unexpected exception classification")
    save(".artifacts/proposed-registry.json", dict(schema_version=1, exceptions=rows))
    package = HERE / ".artifacts/two-piece-package"
    records.append(run("native-proposed-registry", ["python3", MASTER / "scripts/lab/native_predeploy.py", "--package", package,
        "--inputs", package / "native-checks/native-gates.json", "--exceptions", HERE / ".artifacts/proposed-registry.json"]))
    records.append(run("auto-identical-preview", ["python3", MASTER / "scripts/lab/auto_approve_exceptions.py",
        "--candidate", HERE / "evidence/native-candidate.json", "--baseline", HERE / "evidence/native-u12.json"]))
    policy = json.loads((HERE / "policy-build-receipt.json").read_text())
    host = json.loads((HERE / "host-build-receipt.json").read_text())
    delta = {}
    for role in ["host", "policy"]:
        before = json.loads((HERE / "evidence" / ("open-" + role + "-u12.json")).read_text())
        after = json.loads((HERE / "evidence" / ("open-" + role + "-candidate.json")).read_text())
        def count(report, kind):
            return sum(row["kind"] == kind for row in report["findings"])
        delta[role] = dict(before_sites=len(before["binaries"][0]["sites"]), after_sites=len(after["binaries"][0]["sites"]),
            before_edges=len(before["binaries"][0]["namespace_edges"]), after_edges=len(after["binaries"][0]["namespace_edges"]),
            repeats_before=count(before, "INHERIT-REPEAT"), repeats_after=count(after, "INHERIT-REPEAT"),
            after_open_before=count(before, "INHERIT-AFTER-OPEN"), after_open_after=count(after, "INHERIT-AFTER-OPEN"),
            same_site_callees=[row["callee"] for row in before["binaries"][0]["sites"]] == [row["callee"] for row in after["binaries"][0]["sites"]],
            same_edge_callees=[row["callee"] for row in before["binaries"][0]["namespace_edges"]] == [row["callee"] for row in after["binaries"][0]["namespace_edges"]])
    save("open-delta.json", delta)
    expected_path = MASTER / "benchmark/2026-10-02-u10-1-t8-rerun/expected-run.json"
    expected = json.loads(expected_path.read_text())
    save("deployed-identity.json", dict(path=portable(expected_path), sha256=sha(expected_path),
        per_board={board: {name: digest for name, digest in row["expected"].items()
            if name.endswith(("/appspawn-x", "/libnativeloader.so"))} for board, row in expected["boards"].items()},
        note="deployed_whois --generation locates this bundle's copies, but its map section still scans signed U9; never relabel those maps as U10.1T8."))
    origin = REPO / "benchmark/2026-10-02-bms-source-reconcile/sources/bms/src/adapter/framework/app-native-loader/src"
    excerpts = []
    for filename, spans in [("app_native_loader.c", [(60, 69), (440, 480)]), ("flutter_domain.inc", [(18, 45)])]:
        path = origin / filename
        lines = path.read_text().splitlines()
        excerpts.append(dict(path=portable(path), sha256=sha(path),
            lines=[dict(number=number, text=lines[number - 1]) for start, end in spans for number in range(start, end + 1)]))
    save("evidence/mcdonalds-existing-private-route.json", excerpts)
    def delivered(record):
        item = record["artifacts"]["candidate1"]
        return dict(path=item["path"].replace("$REPO/", "$WORKSPACES/westlake-harness-bms/"), sha256=item["sha256"])
    targets = {
        "native/payload/android/lib64/libnativeloader.so": dict(candidate=delivered(policy), before=POLICY_SHA, rollback="restore U12 2a6ec73f bytes"),
        "native/payload/route/libnativeloader.so": dict(candidate=delivered(policy), before=POLICY_SHA, rollback="restore the same U12 bytes in both aliases together"),
        "native/payload/runtime/appspawn-x": dict(candidate=delivered(host), before=HOST_SHA, rollback="restore U12 2a87118e bytes")}
    save("payload-edit.json", dict(execution_enabled=False, targets=targets, runtime_changed=False, compat_changed=False,
        final_assembly_owner="cx-t0", no_root_zlib_alias=True, no_libc_copy=True))
    save("predictions.json", dict(rows=[
        dict(key="cv2-com-chessclock-android", conditional_first_fatal_moves=1, incremental_over_u12=1,
            current_wall="window5 hilog:43043 media_jni absent from system manifest at MediaPlayer.clinit:620",
            conditions="unique runtime resident handle must be available in the sealed callback; MediaPlayer natives stay registered",
            next_first_fatal="unknown", t20="unknown", decoding_proved=False),
        dict(key="mcdonalds", conditional_first_fatal_moves_from_window5=1, incremental_over_u12=0,
            current_wall="window5 hilog:30948 librealmc NEEDED libz missing -> provider ULE -> hilog:31141 DI NPE",
            reason="eebd ANL already selects westlake_native for McDonald; U12 supplies the previously absent private alias/provider. This new whitelist literal duplicates that directory in the selected path, not a newly proven owner edge.",
            conditions="actual U12 result and relocation owner scope must be checked; 221 available exports are not runtime resolution proof",
            next_first_fatal="unknown", t20="unknown")], no_lighting_claim=True, execution_enabled=False))
    save("offline_precheck.json", dict(execution_enabled=False, evidence_only=True,
        expect=dict(confirm="Chessclock same PID clears media_jni manifest wall via existing resident runtime; McDonald logs existing private zlib owner/route and old libz error vanishes (do not double-count U12 gain).",
                    refute="media owner NOLOAD fails or a second runtime maps; McDonald still lacks libz or a new private-owner import fails; retain evidence and restore exact baseline."),
        prewindow_requirements=["outer review and exact final U13 manifest rebind", "full ABI/calls/consumer and N1/N2 on assembled runtime+VLC compat+these pieces", "signed rollback and regression probes"]))
    save("gate-summary.json", dict(commands=records, exception_matched=157, exception_new=0,
        master_registry_modified=False, proposed_registry_replay_pass=True,
        final_manifest_admitted=False, jar_changed=False, execution_enabled=False))
    save("results.json", dict(policy_candidate=delivered(policy), host_candidate=delivered(host),
        baselines=dict(policy=POLICY_SHA, host=HOST_SHA), exact_reproduction=True, repeat_builds_identical=True,
        namespace_delta=delta, new_n1=0, new_n2=0, new_exception_findings=0,
        abi_export_call_consumer_differences=0,
        expected_first_fatal_moves=dict(chessclock_conditional=1, mcdonalds_incremental_over_u12=0),
        execution_enabled=False, board_touched=False, current_bundle_modified=False))
    print("two-piece audit: 157 auto-identical / 0 new; proposed-registry replay PASS; final U13 admission pending")


if __name__ == "__main__":
    main()
