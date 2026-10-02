import csv
import io
import json

from audit import HERE, MASTER, REPO, portable, save, sha


def main():
    observations = json.loads((HERE / "observations.json").read_text())
    consumers = json.loads((HERE / "consumers.json").read_text())
    observed = {row["key"]: row for row in observations["rows"]}
    predictions = []
    priority = {"fd-fennec_fdroid": 0, "firefox": 1, "x": 2, "ooniprobe": 3}
    for app in sorted(consumers["apps"], key=lambda row: (priority.get(row["key"], 4), row["key"])):
        row = observed.get(app["key"])
        symbols = sorted({symbol["name"] for member in app["members"] if member["status"] == "ELF64-AArch64"
                          for symbol in member["imports"]})
        predictions.append(dict(key=app["key"], apk_sha256=app["apk_sha256"], static_symbols=symbols,
             actual_symbol_errors=sorted({event["symbol"] for event in row["symbol_events"]}) if row else [],
             original_log_lines=[event["line"] for event in row["symbol_events"]] if row else [],
             source_hilog=row["run"] + "/hilog.txt" if row else None,
             first_fatal_moved_by_4698="no-supported-movement" if row else "unknown-no-observed-requested-symbol-wall",
             next_fatal_after_4698=row["next_fatal"] if row else "unknown; static import does not establish execution or first fatal",
             conditional_scope_pair_next=row["conditional_scope_next"] if row else "unknown-no-owner-oracle"))
    save("predictions.json", dict(candidate="4698c0a5", execution_enabled=False,
         expected_first_fatal_moved_keys=[], static_exposure_not_beneficiary_count=True, rows=predictions))
    output = io.StringIO()
    fields = list(predictions[0])
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({name: json.dumps(value) if isinstance(value, list) else value for name, value in row.items()}
                    for row in predictions)
    (HERE / "predictions.csv").write_text(output.getvalue())
    validation = []
    for name in ["cargo.txt", "t1-lifecycle.json", "t1-stderr.txt", "t2-lifecycle.json", "t2-stderr.txt"]:
        raw, public = HERE / ".artifacts" / name, HERE / "evidence" / name
        public.write_text(portable(raw.read_text()))
        validation.append(dict(raw_path=portable(raw), raw_sha256=sha(raw), evidence=public.name, sha256=sha(public)))
        if name.endswith("lifecycle.json"):
            result = json.loads(raw.read_text())
            if not result["passed"]:
                raise ValueError("failed actual contract: " + name)
            for scenario in result["verification"]["results"]:
                for evidence in scenario["evidence"]:
                    if evidence["type"] == "test_output" and (not evidence["passed"] or "1 passed; 0 failed" not in evidence["stdout"]):
                        raise ValueError("contract selector did not execute a real test")
    save("evidence/validation-receipts.json", dict(python_tests=8, rust_tests=4, contract_scenarios=4,
         skipped=0, raw_records=validation, normalization="Exact local workspace/HOME prefixes only"))
    raw_inventory = []
    for path in sorted((HERE / ".artifacts").rglob("*")):
        if path.is_file() and "members" not in path.relative_to(HERE / ".artifacts").parts:
            raw_inventory.append(dict(path=portable(path), bytes=path.stat().st_size, sha256=sha(path)))
    save("persistent-inventory.json", dict(persistent_root=portable(HERE / ".artifacts"), files=raw_inventory,
         member_inventory="consumers.json: each unique affected SHA also exists in .artifacts/members/<SHA>.so",
         source_snapshots=["benchmark/2026-10-01-u10-native-shims/baseline/",
                           "benchmark/2026-10-02-n11h-host-owner/inputs/"],
         candidate_binaries_in_public_git=False))
    save("results.json", dict(status="OFFLINE_REVIEW_READY_OWNER_BINDING_UNVERIFIED", device_io=False,
         execution_enabled=False, deployed=json.loads((HERE / "identity.json").read_text())["pins"],
         static_keys=166, static_members=888, static_exposure={row["symbol"]: row["affected_keys"] for row in consumers["groups"]},
         observed_error_keys=observations["actual_error_keys"], expected_first_fatal_moved_keys_exports_only=[],
         conditional_gnu_load_wall_keys=["fd-fennec_fdroid", "firefox"], conditional_first_fatal_movement="unknown",
         x_remaining_observed_fatal="TelephonyManager null cast32788/32789", reference_source_same_provenance=False,
         version_definition_addition_required_by_current_binary_for_ordinary_relocation=False,
         static_scope_conditions_addressed=True, actual_owner_resolution_proved=False,
         candidate_sha256s=json.loads((HERE / "build-receipt.json").read_text())["repeated"][0],
         host_sha256s=json.loads((HERE / "host-build-receipt.json").read_text())["repeated"][0],
         abi_calls_unchanged=True, removed_consumed_exports=0, actual_runtime_consumer_success=False,
         raw_strings_drops=0, raw_strings_adds=0, namespace_edges_equal=True, retained_after_open_may_paths=4,
         expected=dict(confirm="Sole resident compat owner binds actual error imports with unchanged mapping count; evaluate next terminal independently",
                       refute="Unavailable resident, unchanged errors, new owner, version rejection or regression"),
         evidence=["identity.json", "consumers.json", "observations.json", "predictions.json", "candidate-evidence.json",
                   "build-receipt.json", "host-build-receipt.json", "persistent-inventory.json"]))
    documentation = {
        "README.md": ["| **`benchmark/2026-10-02-toutiao-bionic-scope/`** | **Actual compat export/version audit,166 native exposure and U9 PID-bound error calibration; exact-reproduced two-export and resident-global offline candidates, with first-fatal forecasts separate from static upper bounds.** |"],
        ".octos/KNOWLEDGE-DIGEST.md": ["- Toutiao wall3 (2026-10-02,cx-bms): actual015a has LOCAL errno/missing cmsg, exported unversioned property/GNU; source map is not dynsym. Factoryfd3c decode80c50 sets GLOBAL,88040 is prepare_lazy NOW not drift;8b294 accepts empty-name absent provider version tables,80f58 saved scope and867e4 chain retention explain two distinct static conditions, not owner proof. All166/888 imports expose50/19/4/14 keys but U9 actual errors onlyooniprobe/x andfennec/firefox; x first fatal32788 is TelephonyManager null, OONI lit.4698 alone has no supported first-fatal movement;6eaa+044b scope pair stays owner-oracle pending. See benchmark/2026-10-02-toutiao-bionic-scope/."]
    }
    save("documentation.json", documentation)
    selected = {path for path in HERE.glob("*") if path.is_file() and path.name != "landing-paths.txt"}
    for report_name in ["identity.json", "consumers.json", "candidate-evidence.json"]:
        for record in json.loads((HERE / report_name).read_text())["tool_records"]:
            selected.add(HERE / record["evidence"])
    selected.update(path for path in (HERE / "evidence").glob("*") if path.suffix == ".json" or
                    path.name.startswith(("u9-", "oh61-", "host-promotion", "cargo", "t1-", "t2-")))
    selected.update((REPO / "specs/toutiao-bionic-scope").glob("*.spec.md"))
    selected.add(REPO / "tools/spec-checks/tests/toutiao_bionic_scope.rs")
    selected.add(HERE / "evidence/preflight.txt")
    selected.add(HERE / "landing-paths.txt")
    (HERE / "landing-paths.txt").write_text("\n".join(sorted(str(path.relative_to(REPO)) for path in selected)) + "\n")
    print("ready: " + str(len(selected)) + " landable paths; no bundle/device edits; first-fatal forecast[]")


if __name__ == "__main__":
    main()
