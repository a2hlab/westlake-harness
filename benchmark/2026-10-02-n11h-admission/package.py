import copy
from datetime import datetime
import hashlib
import importlib.util
import json

from settings import ACCEPTED, ARTIFACTS, BASE_SHA, HERE, HOST_SHA, INPUTS_SHA, MANIFEST_SHA, MASTER, candidate_report, file, load, reference, save, sha


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def raw_strings():
    reader = module("accepted_readonly", file(ACCEPTED + "/elf_readonly.py"))
    baseline, candidate = ARTIFACTS / "baseline/appspawn-x", ARTIFACTS / "candidate/appspawn-x"
    if sha(baseline) != BASE_SHA or sha(candidate) != HOST_SHA:
        raise ValueError("accepted ELF drift")
    old, new = reader.rodata_strings(baseline), reader.rodata_strings(candidate)
    return {"DROPPED": old - new, "ADDED": new - old}


def string_review():
    header = ACCEPTED + "/n11h-owner.h"
    source = ACCEPTED + "/src/candidate-stock-host.c"
    resident = ACCEPTED + "/inputs/resident-compat.h"
    build = ACCEPTED + "/build.py"
    rows = []
    for direction, values in raw_strings().items():
        for value in sorted(values):
            witnesses = []
            if direction == "DROPPED" and value.startswith("/"):
                suffix = value[value.index("/benchmark/") + 1:]
                shown = "$REPO/" + suffix
                witnesses = [reference(build, "-ffile-prefix-map="), reference(build, "if variant == \"baseline\":")]
                reason = "Old absolute __FILE__ identity is deliberately replaced by the portable candidate file-prefix mapping. No load path or policy permission is removed."
                if value.endswith("resident-compat.h"):
                    witnesses.append(reference(resident, "owner_verified view="))
                else:
                    witnesses.append(reference(source, "[N11h-HOST-OWNER] action=inherit"))
            elif direction == "DROPPED":
                shown = value
                witnesses = [reference(ACCEPTED + "/inputs/host-r3.c", '"' + value + '"'), reference(header, "#define N11H_PRIVATE_LIBS")]
                reason = "Replace the private four-library whitelist with the same four entries plus the bridge owner in the original single sealed inherit. No original private permission disappears."
            elif value.startswith("benchmark/"):
                shown = value
                witnesses = [reference(build, '"=."]')]
                if value.endswith("n11h-owner.h"):
                    witnesses.append(reference(header, "[N11h-HOST-OWNER] action=resident-check"))
                elif value.endswith("resident-compat.h"):
                    witnesses.append(reference(resident, "owner_verified view="))
                else:
                    witnesses.append(reference(source, "[N11h-HOST-OWNER] action=inherit"))
                reason = "New portable __FILE__ identity in APPSPAWN logging, from -ffile-prefix-map. Not a runtime library search path."
            elif value.startswith("[%{public}s:"):
                shown = value
                literal = value.split("][", 1)[1]
                literal = "[" + literal
                owner = header if "resident-check" in literal else source
                witnesses = [reference(owner, literal)]
                reason = {
                    "resident-check": "Expose real NOLOAD query outcome for each sealed owner; NULL/ENOENT is not success.",
                    "action=inherit": "Expose the actual once-only sealed inherit whitelist and return code before fresh opens.",
                    "action=reject target": "Expose missing sealed-owner namespace rejection, without default fallback.",
                    "action=reject path": "Expose protected-owner aliases or missing owner rejection; never open an alternate copy.",
                    "action=%{public}s": "Expose canonical-owner resident-return or rejection in StockOpenNamespace; action label and rc must be interpreted, not mere marker presence."
                }[next(needle for needle in ["resident-check", "action=inherit", "action=reject target", "action=reject path", "action=%{public}s"] if needle in literal)]
            elif value in {"reject", "resident"}:
                shown = value
                witnesses = [reference(source, '"' + value + '"')]
                reason = "Exact action label for the host-open outcome log, separating successful resident-handle lookup from rejection; does not establish relocation."
            else:
                shown = value
                witnesses = [reference(header, '"' + value + '"')]
                reason = {
                    "/system/android/lib64/liboh_adapter_bridge.so": "Canonical bridge-owner path for sealed NOLOAD checks and exact StockOpen matching; no alternate root is permitted.",
                    "liboh_adapter_bridge.so": "Protected owner basename: reject basename/alias requests that fail canonical matching instead of app/default loading.",
                    "liboh_android_runtime.so": "Protected runtime basename: reject aliases rather than loading another runtime.",
                    "liboh_adapter_bridge.so:liboh_android_runtime.so": "Minimal sealed owner permissions shared by bridge and ordinary app domains, before bootstrap, once per pair.",
                    "liboh_adapter_bridge.so:liboh_android_runtime.so:libbionic_compat.so": "Merge verified sealed compat into the existing owner edge; no second inherit overwrites that pair.",
                    "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:liboh_adapter_bridge.so": "Private whitelist is original four plus bridge owner, not a new system-root or private-branch removal."
                }[value]
            rows.append(dict(id=direction + "-" + str(sum(row["direction"] == direction for row in rows) + 1).zfill(2),
                             direction=direction, value_template=shown, value_sha256=hashlib.sha256(value.encode()).hexdigest(),
                             allow_reason=reason, source=witnesses, outer_checked=False, decision="PENDING"))
    if len(rows) != 19 or sum(row["direction"] == "DROPPED" for row in rows) != 3:
        raise ValueError("unexpected string delta")
    return dict(schema_version=1, state="PENDING_OUTER_REVIEW", baseline_sha256=BASE_SHA,
                candidate_sha256=HOST_SHA, dropped=3, added=16, items=rows,
                scope="Exact string-value hashes only. No broad path/policy waiver; no allowance was applied to deployed_strings_diff.")


def body(row, ignore_evidence_line=False):
    result = {name: copy.deepcopy(value) for name, value in row.items() if name not in {"issue_id", "disposition", "exception"}}
    if ignore_evidence_line:
        def strip(value):
            if isinstance(value, list):
                return [strip(item) for item in value]
            if isinstance(value, dict):
                return {name: strip(item) if name != "evidence" else {key: strip(part) for key, part in item.items() if key != "line"}
                        for name, item in value.items()}
            return value
        result = strip(result)
    return result


def identity(gate, report, finding):
    bound = dict(gate=gate, package_manifest_sha256=report["package_manifest_sha256"],
                 inputs_sha256=report["inputs_sha256"], finding=body(finding))
    return hashlib.sha256(json.dumps(bound, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exceptions(now):
    baseline, candidate = load(ACCEPTED + "/evidence/native-r3.txt"), candidate_report()
    registry = json.loads((MASTER / "knowledge/gates/native-predeploy-exceptions.json").read_text())
    if baseline["gates"]["N2"]["details"] != candidate["gates"]["N2"]["details"]:
        raise ValueError("N2 details drift")
    deltas, unmatched, matches = {}, {}, {}
    for gate in ["N2", "N1"]:
        parents = baseline["gates"][gate]["findings"]
        matched_ids, rows, new_rows, match_rows = set(), [], [], []
        for finding in candidate["gates"][gate]["findings"]:
            if identity(gate, candidate, finding) != finding["issue_id"]:
                raise ValueError("candidate issue binding mismatch")
            equivalent = [parent for parent in parents if body(parent, gate == "N1") == body(finding, gate == "N1")]
            if not equivalent:
                new_rows.append(finding)
                continue
            if len(equivalent) != 1:
                raise ValueError("ambiguous parent match")
            parent = equivalent[0]
            if identity(gate, baseline, parent) != parent["issue_id"] or parent["disposition"] != "EXCEPTED":
                raise ValueError("unapproved parent finding")
            if parent["exception"] not in registry["exceptions"] or parent["issue_id"] in matched_ids:
                raise ValueError("parent registry drift or duplicate reuse")
            matched_ids.add(parent["issue_id"])
            evidence = list(dict.fromkeys([ACCEPTED + "/evidence/native-candidate.txt", ACCEPTED + "/evidence/native-r3.txt",
                                          *parent["exception"]["evidence"]]))
            for name in evidence:
                file(name)
            reason = "Identical to approved r3 finding " + parent["issue_id"] + "; "
            reason += "N2 details and finding body exact" if gate == "N2" else "finding body exact except relocated evidence line numbers"
            reason += ". Proposed auto-identical rebind only; no broader removal condition or window authority."
            rows.append(dict(gate=gate, package_manifest_sha256=MANIFEST_SHA, inputs_sha256=INPUTS_SHA,
                             issue_id=finding["issue_id"], reason=reason,
                             removal_condition=parent["exception"]["removal_condition"], evidence=evidence,
                             approved_by="auto-identical(outer rule 2026-10-01)", approved_at=now,
                             auto_from=dict(package_manifest_sha256=baseline["package_manifest_sha256"],
                                            inputs_sha256=baseline["inputs_sha256"], issue_id=parent["issue_id"])))
            match_rows.append(dict(gate=gate, parent_issue_id=parent["issue_id"], issue_id=finding["issue_id"],
                                   match="exact" if gate == "N2" else "exact-except-evidence-line",
                                   body_sha256=hashlib.sha256(json.dumps(body(finding, gate == "N1"), sort_keys=True).encode()).hexdigest()))
        if len(matched_ids) != len(parents):
            raise ValueError("missing parent finding")
        deltas[gate] = dict(schema_version=1, state="PENDING_OUTER_ADOPTION", exceptions=rows)
        unmatched[gate], matches[gate] = new_rows, match_rows
    if len(deltas["N2"]["exceptions"]) != 103 or len(deltas["N1"]["exceptions"]) != 53 or unmatched["N2"] or len(unmatched["N1"]) != 1:
        raise ValueError("unexpected finding delta")
    finding = unmatched["N1"][0]
    if finding["detail"]["function"] != "N11hResidentHandle" or finding["detail"]["evidence"]["line"] != 29:
        raise ValueError("new N1 changed")
    header = ACCEPTED + "/n11h-owner.h"
    source = ACCEPTED + "/src/candidate-stock-host.c"
    review = dict(schema_version=1, state="PENDING_OUTER_REVIEW", gate="N1", package_manifest_sha256=MANIFEST_SHA,
                  inputs_sha256=INPUTS_SHA, issue_id=finding["issue_id"], finding=body(finding), outer_checked=False,
                  source=[reference(header, "dlopen_ns(owner, path"), reference(header, "N11hResidentHandle(owner, N11H_BRIDGE_PATH"),
                          reference(header, "N11hResidentHandle(owner, N11H_RUNTIME_PATH"), reference(source, "dlns_get(N11H_OWNER_NS"),
                          reference(source, "const char *owner_path = N11hOwnerPath(path)"), reference(source, "N11hResidentHandle(&owner, owner_path")],
                  lineage=dict(parent_report=ACCEPTED + "/evidence/native-r3.txt", accepted_commit="3b05c71c1c",
                               parent_queries=[parent["issue_id"] for parent in baseline["gates"]["N1"]["findings"] if parent.get("profile") == "u10-1-resident-compat"],
                               basis="Existing r3 NOLOAD-only resident-compat probes are precedent, not a semantic match or approval of this new parameter-target site."),
                  no_new_copy=dict(owner="westlake.sealed.child", flags="RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD (6)",
                                   targets=["/system/android/lib64/liboh_adapter_bridge.so", "/system/android/lib64/liboh_android_runtime.so"],
                                   static_sites=["StockOpenNamespace@0xda24", "N11hCheckOwners@0xdb38", "N11hCheckOwners@0xdba0"],
                                   argument="The helper probes canonical owners only via the existing sealed handle. NOLOAD cannot load a new object; a missing owner returns NULL/ENOENT. StockOpen rejects protected aliases and has no app/default fallback for these owners.",
                                   limitation="Other baseline private runtime fresh-open paths remain. This is not a process-wide single-copy or board relocation proof."),
                  evidence=[ACCEPTED + "/evidence/native-candidate.txt", ACCEPTED + "/evidence/open-candidate.json",
                            ACCEPTED + "/evidence/open-r3.json", header, source],
                  removal_condition="Re-review any source, canonical target, namespace, flags, package/input binding or call-site drift; require board owner load-base and control evidence independently before a window.")
    for name in review["evidence"]:
        file(name)
    common = module("native_admission_common", file("scripts/lab/native_gate_common.py"))
    simulated = {}
    for label, proposals in [("N2-only", deltas["N2"]["exceptions"]),
                              ("N2-and-existing-N1", deltas["N2"]["exceptions"] + deltas["N1"]["exceptions"])]:
        simulated[label] = {}
        for gate in ["N1", "N2"]:
            result = common.apply_exceptions(gate, [body(row) for row in candidate["gates"][gate]["findings"]],
                                             MANIFEST_SHA, INPUTS_SHA, dict(schema_version=1, exceptions=proposals))
            simulated[label][gate] = {name: result[name] for name in ["rejected", "excepted", "stale"]}
            simulated[label][gate]["rejected_ids"] = [row["issue_id"] for row in result["findings"] if row["disposition"] == "REJECT"]
    return deltas, review, dict(schema_version=1, device_access=False, live_registry_modified=False,
                               match_rule="N2 exact; N1 ignores only recursively nested evidence.line, no other fields",
                               lineage=matches, simulation=simulated, full_candidate_gate="REJECT pending new N1 review")


def main():
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    strings = string_review()
    deltas, review, comparison = exceptions(now)
    save(HERE / "strings-allow.json", strings)
    save(HERE / "registry-delta.json", deltas["N2"])
    save(HERE / "n1-existing-registry-delta.json", deltas["N1"])
    save(HERE / "outer-review.json", review)
    save(HERE / "evidence/exception-lineage.json", comparison)
    checklist = ["# Exact string allowance proposals", "", "All nineteen boxes are unchecked. Accepting the source does not approve these allowances.", "",
                 "Raw deployed_strings_diff remains rc=1 (3 dropped / 16 added). Value hashes bind the actual raw UTF-8 strings; `$REPO` only redacts old file identities for publication.", ""]
    for row in strings["items"]:
        checklist.extend(["- [ ] **" + row["id"] + "** `" + row["value_template"] + "`",
                          "  - Raw value SHA256: `" + row["value_sha256"] + "`.",
                          "  - Reason: " + row["allow_reason"],
                          "  - Source: " + ", ".join("`" + witness["path"] + ":" + str(witness["line"]) + "`" for witness in row["source"]) + ".", ""])
    (HERE / "STRINGS-CHECKLIST.md").write_text("\n".join(checklist))
    print("strings: 3 DROPPED + 16 ADDED; 19 unchecked proposals")
    print("registry-delta: N2 103 exact auto-identical proposals; all evidence paths exist")
    print("existing N1: 53 separately proposed, evidence.line only normalization")
    for label, gates in comparison["simulation"].items():
        print("simulation " + label + ": " + "; ".join(gate + " rejected=" + str(row["rejected"]) + " excepted=" + str(row["excepted"]) for gate, row in gates.items()))
    print("new N1 " + review["issue_id"] + ": PENDING_OUTER_REVIEW; no approval/no live registry write")


if __name__ == "__main__":
    main()
