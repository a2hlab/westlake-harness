import json
from pathlib import Path

from audit import HERE, MASTER, REPO, portable, save, sha


def main():
    records = []
    selectors = []
    for name in ["cargo.txt", "t1-lifecycle.json", "t1-stderr.txt", "t2-lifecycle.json", "t2-stderr.txt"]:
        raw = HERE / ".artifacts" / name
        public = HERE / "evidence" / name
        public.write_text(portable(raw.read_text()))
        records.append(dict(raw_path=portable(raw), raw_sha256=sha(raw),
                            published_path=portable(public), published_sha256=sha(public)))
        if name.endswith("lifecycle.json"):
            result = json.loads(raw.read_text())
            if not result["passed"]:
                raise ValueError("contract failed: " + name)
            for scenario in result["verification"]["results"]:
                for evidence in scenario["evidence"]:
                    if evidence["type"] == "test_output":
                        if not evidence["passed"] or "1 passed; 0 failed" not in evidence["stdout"]:
                            raise ValueError("selector did not run an actual passing test")
                        selectors.append(evidence["test_name"])
    if len(set(selectors)) != 4:
        raise ValueError("four distinct Rust selectors required")
    save("evidence/validation-receipts.json", dict(records=records, selectors=selectors,
         normalization="Exact local workspace prefixes only; raw stdout retained locally",
         python_tests=8, rust_tests=4, contract_scenarios=4, skipped=0))
    paths = [MASTER / "benchmark/2026-10-01-installation-chain-identity/current-u9.json"]
    paths += [MASTER / ("benchmark/2026-10-02-u10-1-t8-rerun/window/restored-" + board + ".json")
              for board in ["5ea", "5cd", "61b"]]
    save("evidence/service-identity-receipts.json", dict(scope="Existing recorded service assertions, not fresh live reads",
         files=[dict(path=portable(path), sha256=sha(path)) for path in paths]))
    installations = json.loads((HERE / "installations.json").read_text())
    save("results.json", dict(schema_version=1, status="OFFLINE_REVIEW_READY_NOT_WINDOW_APPROVED",
         device_access=False, execution_enabled=False, recommendation=dict(target="51e1b525",
         replace_boards=["5ea", "5cd"], verify_only=["61b"], aliases_per_board=2),
         differences=dict(compiled_exact_payload_exceptions=4, whole_apk_sha_runtime_predicate=False,
         raw_strings_dropped=29, raw_strings_added=41, raw_strings_exit=1,
         direct_rodata_dropped=1, direct_rodata_added=12, exports_old=1096, exports_new=1096,
         exports_added=0, exports_removed=0, call_set_added=["strlen"],
         stripped_call_label_is_not_behavioral_attribution=True, consumer_samples=0,
         open_sites_old=2, open_sites_new=2, namespace_edges_old=0, namespace_edges_new=0,
         retained_default_ns_findings_per_binary=2),
         observed_installations={label: installations[label] for label in
             ["signed166", "signed_other165", "additional_diagnostic_attempts", "pooled_observed_attempts"]},
         other165_impact=dict(direct_exception_target_keys=["fd-seal"], strict_default_keys=164,
         strict_default_basis="source inference, not paired full-corpus validation",
         observed_other_keys_with_new_binary=55, fresh_install_regression_pending=True),
         gates=dict(python_tests=8, rust_tests=4, contract_scenarios=4, skipped=0,
         actual_offline_dry_runs=2, raw_strings_allowance_pending=True,
         service_client_consumer_gate_pending=True, mapped_current_installd_identity_pending=True),
         evidence=["artifacts.json", "installations.json", "alignment-plan.json",
                   "evidence/validation-receipts.json", "evidence/service-identity-receipts.json"]))
    documentation = {
        "README.md": ["| **`benchmark/2026-10-02-libinstalls-unification/`** | **Offline 2c/51 installation-service lineage, actual ELF payload table and disassembly, 166 signed plus three failed install attempts, and disabled two-alias alignment/rollback proposal.** |"],
        ".octos/KNOWLEDGE-DIGEST.md": ["- libinstalls split (2026-10-02, cx-bms): runtime-bundle/app-map WHOIS does not cover installd. New51e1 permits only four bundle/ABI/name/content-SHA tuples, not whole-APK SHA; CRC/owner/mode remain. Stripped CFI strlen labeling is not callback behavior proof. Signed166 success plus three retained old5ea failures are not a paired regression; bm rc0 can still print9568260. Both service aliases already belong to the extended123 fingerprint; propose only5ea/5cd to archived51e1, retain current companions and require fresh mapped-owner/consumer/regression gates. See benchmark/2026-10-02-libinstalls-unification/."]
    }
    save("documentation.json", documentation)
    paths = [path for path in HERE.rglob("*") if path.is_file()
             and not any(part in {".artifacts", "__pycache__"} for part in path.relative_to(HERE).parts)
             and path.name not in {"symbol-lineage.txt", "landing-paths.txt", "preflight.txt"}]
    paths += list((REPO / "specs/libinstalls-unification").glob("*.spec.md"))
    paths.append(REPO / "tools/spec-checks/tests/libinstalls_unification.rs")
    paths += [HERE / "landing-paths.txt", HERE / "evidence/preflight.txt"]
    listing = sorted(str(path.relative_to(REPO)) for path in paths)
    (HERE / "landing-paths.txt").write_text("\n".join(listing) + "\n")
    print("finalized: four actual Rust selectors; Python8/Rust4/scenarios4; " + str(len(listing)) + " landing paths")


if __name__ == "__main__":
    main()
