import csv
import difflib
import io
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from class_contracts import contract, parse_blocks
from common import ASSEMBLY, HERE, MASTER, PRIOR, capture, expand, load, portable, save, sha
from strict_findings import canonical, differences, field_proof, finding, issue_id
import generation_bundle as bundle
import generation_static_checks as static

STUBS_COMMIT = "af64eee3dc565e85a32a8d3750a7f77d409f7555"
JAR_COMMIT = "d97ebf29b111a7bd13ff14e92289b3b1622e67ff"


def git_source(relative, commit):
    path = MASTER / relative
    expected = subprocess.check_output(["git", "-C", str(MASTER), "show", commit + ":" + relative])
    if path.read_bytes() != expected:
        raise ValueError("Source differs from pinned commit: " + relative)
    snapshot = HERE / "inputs/source" / path.name
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, snapshot)
    return dict(path=path, commit=commit, sha256=sha(path), git_blob_matches=True, snapshot=snapshot)


def dump_jar(jar, label, tool):
    blocks, receipts = {}, []
    with zipfile.ZipFile(jar) as archive:
        for name in sorted(item for item in archive.namelist() if re.fullmatch(r"classes\d*\.dex", item)):
            dex = HERE / ".artifacts/dex" / label / name
            dex.parent.mkdir(parents=True, exist_ok=True)
            dex.write_bytes(archive.read(name))
            raw = HERE / ".artifacts/dex" / label / (name + ".dexdump.txt")
            with raw.open("wb") as output:
                result = subprocess.run([tool, "-l", "plain", dex], stdout=output, stderr=subprocess.PIPE)
            if result.returncode:
                raise ValueError("dexdump failed: " + result.stderr.decode(errors="backslashreplace"))
            parsed = parse_blocks(raw.read_text(encoding="utf-8", errors="backslashreplace"))
            if set(parsed) & set(blocks):
                raise ValueError("Duplicate classes across DEX files")
            blocks.update(parsed)
            receipts.append(dict(dex=name, dex_sha256=sha(dex), raw=raw, raw_sha256=sha(raw), exit_code=result.returncode, classes=len(parsed)))
    if not blocks:
        raise ValueError("Nonempty complete JAR required")
    return blocks, receipts


def classes(package, baseline):
    tool = sorted((Path.home() / "Library/Android/sdk/build-tools").glob("*/dexdump"))[-1]
    jar_reviews = [row for row in load(ASSEMBLY / "jar-review.json")["members"] if row["allow_add_preview"]]
    source_manager = git_source("benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdManager.java", STUBS_COMMIT)
    source_info = git_source("benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdServiceInfo.java", STUBS_COMMIT)
    source_trampoline = git_source("benchmark/2026-10-03-u15-jar-v1/src/adapter/activity/TrampolineFinishOrder.java", JAR_COMMIT)
    keys_path = MASTER / "benchmark/2026-10-03-x-trampoline-handover/evidence/trampoline-keys.txt"
    key_lines = keys_path.read_text().splitlines()
    trampoline_keys = [line.split()[0] for line in key_lines if " [('" in line]
    if len(set(trampoline_keys)) != 36:
        raise ValueError("Expected all 36 measured trampoline keys")
    evidence = HERE / "evidence/trampoline-keys.txt"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(keys_path, evidence)
    cluster_path = MASTER / "benchmark/2026-10-03-u16-wall-clusters/clusters.csv"
    clusters = list(csv.DictReader(cluster_path.open()))
    snapshots = {"cluster-K": next(row for row in clusters if row["cluster"] == "K"), "cluster-M": next(row for row in clusters if row["cluster"] == "M")}
    save("cluster-prediction-sources.json", dict(source=cluster_path, sha256=sha(cluster_path), rows=snapshots))
    old_rows, new_rows = static.effective(baseline), static.effective(package)
    classes_out, jars_out, runs = [], [], []
    for review in jar_reviews:
        target = review["target"]
        old = bundle.member(baseline, old_rows[target])
        new = bundle.member(package, new_rows[target])
        if sha(old) != review["deployed_sha256"] or sha(new) != review["candidate_sha256"]:
            raise ValueError("Exact JAR pair changed")
        label = "nsd" if "stubs" in target else "trampoline"
        before, old_receipts = dump_jar(old, label + "-u14", tool)
        after, new_receipts = dump_jar(new, label + "-u15", tool)
        additions = sorted(set(after) - set(before))
        if additions != sorted(review["allow_add_preview"]) or set(before) - set(after):
            raise ValueError("Unexpected additions or drops")
        runs.append(capture("class-diff-" + label, [sys.executable, MASTER / "scripts/lab/deployed_class_diff.py", new, "--deployed", old, "--frozen"]))
        unchanged_shapes = all(contract(name, before[name])[field] == contract(name, after[name])[field]
            for name in before for field in ["superclass", "interfaces"])
        if not unchanged_shapes:
            raise ValueError("Existing class shape changed")
        jars_out.append(dict(target=target, old=old, new=new, old_sha256=sha(old), new_sha256=sha(new),
            old_class_count=len(before), new_class_count=len(after), additions=additions, dropped=0, reshaped=0,
            extraction=dict(old=old_receipts, new=new_receipts)))
        for descriptor in additions:
            source = source_trampoline if label == "trampoline" else source_info if "/NsdServiceInfo" in descriptor else source_manager
            name = descriptor[1:-1].replace("/", "_")
            proof = HERE / "evidence/classes" / (name + ".dexdump.txt")
            proof.parent.mkdir(parents=True, exist_ok=True)
            proof.write_text(after[descriptor])
            delta = proof.with_suffix(".diff")
            delta.write_text("".join(difflib.unified_diff([], after[descriptor].splitlines(keepends=True),
                fromfile="U14:absent:" + descriptor, tofile="U15:" + descriptor)))
            prediction = dict(served_keys=trampoline_keys if label == "trampoline" else ["fd-immich"],
                cluster="M" if label == "trampoline" else "K", standalone_first_fatal_prediction=0 if label == "trampoline" else None,
                cluster_first_fatal_prediction=0 if label == "trampoline" else 1,
                shared_cluster_credit_not_per_class=True, measured_new_moves=0, new_screenshot_status="not measured",
                before="[ARM938] last ability -> second process; no fatal established" if label == "trampoline" else "bind VerifyError A2.b / unresolved d7.c; later libcronet ATrace relocation",
                after="x own Activity stays in first process; timing/content conditional, other 35 keys first fatal unchanged" if label == "trampoline" else "NSD linking passes; NSD alone leaves ATrace. Full U15 also has Flutter ATrace 9b824502: next Flutter raster wall or unknown, not a lit claim")
            classes_out.append(dict(**contract(descriptor, after[descriptor]), jar=target, source=source,
                prediction=prediction, absent_in_u14=True, exact_add=True, raw_dexdump=proof, raw_dexdump_sha256=sha(proof),
                per_class_diff=delta, per_class_diff_sha256=sha(delta)))
    save("classes.json", dict(classes=classes_out, count=len(classes_out), nsd=8, trampoline=5, source_matches=13,
        comparison=dict(equal_to_u14=0, exact_add=13, unexpected_add=0, dropped=0, reshaped=0), jars=jars_out,
        dexdump=dict(path=tool, sha256=sha(tool)), records=runs, approved=False, execution_enabled=False))
    return runs


def check_evidence(root, item):
    manifest = load(root / "native-checks/scan-manifest.json")
    source = manifest["sources"][item["source"]]
    path = root / "native-checks" / source["path"]
    if sha(path) != source["sha256"]:
        raise ValueError("Scanner source hash changed")
    index = item["line"] - source.get("first_line", 1)
    text = path.read_text().splitlines()[index].strip()
    expected = item["text"].strip()
    if text != expected:
        raise ValueError("Evidence line differs from its frozen source: " + item["source"])
    snapshot = HERE / "inputs/scanner" / (sha(path)[:16] + "-" + path.name)
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, snapshot)
    return dict(path=path, sha256=sha(path), line=item["line"], text=text, exact=True, origin=source.get("origin"),
        snapshot=snapshot, first_line=source.get("first_line", 1))


def registry(package, baseline):
    registry_path = MASTER / "knowledge/gates/native-predeploy-exceptions.json"
    registry_hash = sha(registry_path)
    old_report, new_report, runs = {}, {}, []
    for label, root in [("u14", baseline / "native"), ("u15", package / "native")]:
        runs.append(capture("native-" + label, [sys.executable, MASTER / "scripts/lab/native_predeploy.py", "--package", root,
            "--inputs", root / "native-checks/native-gates.json", "--exceptions", registry_path, "--readelf", "llvm-readelf"]))
        report = load(HERE / ".artifacts/raw" / ("native-" + label + ".txt"))
        if report["errors"]:
            raise ValueError("Native gate error: " + canonical(report["errors"]))
        if label == "u14":
            old_report = report
        else:
            new_report = report
        save("evidence/native-" + label + ".json", report)
    mapping = load(ASSEMBLY / "final-id-mapping.json")
    rows, extra, missing = [], [], []
    for gate in ["N1", "N2"]:
        old = {row["issue_id"]: row for row in old_report["gates"][gate]["findings"]}
        new = {row["issue_id"]: row for row in new_report["gates"][gate]["findings"]}
        mapped = [row for row in mapping if row["gate"] == gate]
        used_old, used_new = set(), set()
        for pair in mapped:
            old_id, new_id = pair["old_issue_id"], pair["final_issue_id"]
            if old_id in used_old or new_id in used_new:
                raise ValueError("Non-bijective registry mapping")
            used_old.add(old_id)
            used_new.add(new_id)
            if old_id not in old or new_id not in new:
                missing.append(dict(gate=gate, old_issue_id=old_id, new_issue_id=new_id))
                continue
            before, after = old[old_id], new[new_id]
            for report, row, expected in [(old_report, before, old_id), (new_report, after, new_id)]:
                if issue_id(gate, row, report["package_manifest_sha256"], report["inputs_sha256"]) != expected:
                    raise ValueError("Issue ID does not bind exact finding")
            changes = differences(finding(before), finding(after))
            line_proofs = []
            if changes:
                for label, root, row in [("old", baseline / "native", before), ("new", package / "native", after)]:
                    detail = row.get("detail", row)
                    evidence = [detail["evidence"]] if "evidence" in detail else []
                    evidence += detail.get("trace", [])
                    line_proofs += [dict(version=label, **check_evidence(root, item)) for item in evidence if "line" in item]
            rows.append(dict(gate=gate, old_issue_id=old_id, new_issue_id=new_id,
                old_manifest_sha256=old_report["package_manifest_sha256"], new_manifest_sha256=new_report["package_manifest_sha256"],
                old_inputs_sha256=old_report["inputs_sha256"], new_inputs_sha256=new_report["inputs_sha256"],
                old_finding=finding(before), new_finding=finding(after), strict_equal=not changes, differences=changes,
                evidence_source_proofs=line_proofs, field_proof={name: field_proof(before, after, name) for name in
                    ["profile", "function", "namespace", "library", "target_expression", "evidence.source", "evidence.line", "evidence.text", "kind", "reason"]},
                sequence_and_full_trace_compared=True, old_approved=before.get("disposition") == "EXCEPTED", issue_ids_recomputed=True))
        extra += [dict(gate=gate, **row) for name, row in new.items() if name not in used_new]
        missing += [dict(gate=gate, removed_old_issue_id=name) for name in old if name not in used_old]
    if sha(registry_path) != registry_hash:
        raise ValueError("Active registry changed during collection")
    save("registry-comparison.json", dict(rows=rows, count=len(rows), strictly_equal=sum(row["strict_equal"] for row in rows),
        different=sum(not row["strict_equal"] for row in rows), new_findings=extra, missing_mappings=missing,
        removed_envelope=["issue_id", "disposition", "exception"], evidence_line_and_sequence_retained=True,
        old_native_manifest_sha256=old_report["package_manifest_sha256"], old_inputs_sha256=old_report["inputs_sha256"],
        new_native_manifest_sha256=new_report["package_manifest_sha256"], new_inputs_sha256=new_report["inputs_sha256"],
        active_registry_sha256_before=registry_hash, active_registry_sha256_after=sha(registry_path), applied=False, approved=False))
    save("changed-findings.json", dict(rows=[row for row in rows if not row["strict_equal"]], new_findings=extra,
        missing_mappings=missing, review_needed=True, reason="Six source-line shifts are not binding metadata; outer must review explicitly"))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["gate", "old_issue_id", "new_issue_id", "strict_equal", "changed_fields"])
    writer.writeheader()
    writer.writerows(dict(gate=row["gate"], old_issue_id=row["old_issue_id"], new_issue_id=row["new_issue_id"],
        strict_equal=row["strict_equal"], changed_fields=";".join(item["path"] for item in row["differences"])) for row in rows)
    (HERE / "registry-mapping.csv").write_text(output.getvalue())
    print("strict registry equal=" + str(sum(row["strict_equal"] for row in rows)) + " different=" + str(sum(not row["strict_equal"] for row in rows)) + " new=" + str(len(extra)), flush=True)
    return runs


def main():
    composition = load(PRIOR / "common/composition.json")
    package, baseline = expand(composition["package"]), expand(composition["transaction_base"])
    for root, expected in [(package, composition["bundle_sha256"]), (baseline, composition["transaction_base_sha256"])]:
        if sha(root / "bundle.json") != expected:
            raise ValueError("Selected bundle changed")
        bundle.validate(root)
    records = classes(package, baseline)
    records += registry(package, baseline)
    save("collection-runs.json", dict(records=records, device_access=False, vm_used=False, registry_written=False,
        execution_enabled=False, selected_u15_bundle_sha256=composition["bundle_sha256"], selected_u14_bundle_sha256=composition["transaction_base_sha256"]))


if __name__ == "__main__":
    main()
