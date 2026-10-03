import csv
import io

from common import HERE, PRIOR, REPO, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static


def main():
    runs = load(HERE / "gate-runs.json")
    variants, increments, images = {}, [], {}
    for variant in ["common", "61b"]:
        composition = load(HERE / variant / "composition.json")
        package, baseline = expand(composition["package"]), expand(composition["transaction_base"])
        if sha(package / "bundle.json") != composition["bundle_sha256"] or sha(baseline / "bundle.json") != composition["transaction_base_sha256"]:
            raise ValueError("Selected package or BASE changed")
        data, _, _ = bundle.validate(package)
        original = load(PRIOR / ".artifacts" / variant / "bundle.json")
        metadata_changes = [name for name in data if data[name] != original[name]]
        if set(metadata_changes) != {"static_checks", "image_gate_reference", "transaction_binding"}:
            raise ValueError("Unexpected bundle metadata changes")
        for field in ["static_checks", "image_gate_reference"]:
            if {name: value for name, value in data[field].items() if name != "baseline_bundle_sha256"} != {name: value for name, value in original[field].items() if name != "baseline_bundle_sha256"}:
                raise ValueError("Unexpected baseline binding metadata changes")
        save(variant + "/metadata-delta.json", dict(fields=metadata_changes, old={name: original[name] for name in metadata_changes},
            new={name: data[name] for name in metadata_changes}, native_bindings_unchanged=True, candidate_artifacts_unchanged=True))
        effective_base = static.effective(baseline)
        images[variant] = [dict(target=row["target"], candidate_sha256=row["sha256"], baseline_sha256=effective_base[row["target"]]["sha256"],
            changed=row["sha256"] != effective_base[row["target"]]["sha256"]) for row in data["boot_group"]["members"] if row["target"] in bundle.IMAGE_TARGETS]
        if len(images[variant]) != 27:
            raise ValueError("Whole 27-member image group is required")
        increments += [dict(variant=variant, **row) for row in composition["increments"]]
        variants[variant] = {name: composition[name] for name in ["package", "bundle_sha256", "transaction_base", "transaction_base_sha256", "native_manifest_sha256", "native_inputs_sha256", "increment_counts", "installers"]}
        variants[variant]["image_group_members"] = 27
        variants[variant]["image_changed_members"] = sum(row["changed"] for row in images[variant])
        save(variant + "/static-policy.json", load(package / data["static_checks"]["policy"]["source"]))
        save(variant + "/paired-receipt.json", load(package / data["paired_build_receipt"]["source"]))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["variant", "layer", "target", "operation", "baseline_sha256", "candidate_sha256"])
    writer.writeheader()
    writer.writerows(increments)
    (HERE / "increments.csv").write_text(output.getvalue())
    save("image-group.json", images)
    save("source-provenance.json", dict(original_compositions=[dict(path=PRIOR / variant / "composition.json", sha256=sha(PRIOR / variant / "composition.json")) for variant in variants],
        native_sources=load(PRIOR / "source-provenance.json"), source_report_sha256=sha(PRIOR / "source-provenance.json"),
        original_bundles=load(HERE / "base-identities.json"), artifacts_rebuilt=False, image_rebaked=False))
    commands = runs["records"]
    if (HERE / "native-delta-gates.json").exists():
        commands += load(HERE / "native-delta-gates.json")["records"]
    if (HERE / "validation-runs.json").exists():
        commands += load(HERE / "validation-runs.json")
    save("results.json", dict(variants=variants, commands=commands, comparison="planned per-board U14 content; no promotion attestation",
        fresh_executor_status={variant: load(HERE / variant / "evidence/executor.json")["status"] for variant in variants},
        image_gates={variant: load(HERE / variant / "evidence/image-gates.json") for variant in variants},
        production_gates_passed=False, execution_enabled=False, promotion_confirmed=False, window_authorized=False,
        device_access=False, lock_taken=False, vm_used=False, active_tables_written=False,
        pending="Outer exact NSD8/trampoline5 review and 204-row registry rebind after U14 windows; real armed U14 BASE and Mac/VM/oatdump replay"))
    lines = ["# Exact fresh Mac command exits", "", "Disabled diagnostic; independent checks do not constitute complete production PASS.", "", "| Evidence | Exit |", "|---|---:|"]
    lines += ["| `" + row["evidence"].split("/")[-1] + "` | " + str(row["exit_code"]) + " |" for row in commands]
    (HERE / "gate-exits.md").write_text("\n".join(lines) + "\n")
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and not path.name.startswith(".") and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u15-on-u14-base").glob("*.spec.md")]
    paths += ["tools/spec-checks/tests/u15_on_u14_base.rs", "benchmark/2026-10-03-u14-on-u13-base/replay-production.sh",
        "benchmark/2026-10-03-u15-final-assembly/replay-production.sh", str((HERE / "listing-receipt.json").relative_to(REPO))]
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), execution_enabled=False))
    print("U15 on U14: disabled, metadata-only; landing=" + str(len(paths)))


if __name__ == "__main__":
    main()
