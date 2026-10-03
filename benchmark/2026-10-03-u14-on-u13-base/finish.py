import csv
import io

from common import HERE, PRIOR, REPO, expand, load, save, sha
import generation_bundle as bundle
import generation_static_checks as static


def main():
    gates = load(HERE / "gate-runs.json")
    variants, all_rows, image_groups = {}, [], {}
    for variant in ["common", "61b"]:
        composition = load(HERE / variant / "composition.json")
        package, baseline = expand(composition["package"]), expand(composition["transaction_base"])
        if sha(package / "bundle.json") != composition["bundle_sha256"] or sha(baseline / "bundle.json") != composition["transaction_base_sha256"]:
            raise ValueError("Selected package or transaction BASE changed")
        data, manifest, _ = bundle.validate(package)
        effective_base = static.effective(baseline)
        image_groups[variant] = [dict(target=row["target"], candidate_sha256=row["sha256"], baseline_sha256=effective_base[row["target"]]["sha256"],
            changed=row["sha256"] != effective_base[row["target"]]["sha256"]) for row in data["boot_group"]["members"] if row["target"] in bundle.IMAGE_TARGETS]
        if len(image_groups[variant]) != 27:
            raise ValueError("Whole 27-member image group is required")
        all_rows += [dict(variant=variant, **row) for row in composition["increments"]]
        variants[variant] = {name: composition[name] for name in ["package", "bundle_sha256", "transaction_base", "transaction_base_sha256", "native_manifest_sha256", "native_inputs_sha256", "increment_counts", "installers"]}
        variants[variant]["image_group_members"] = 27
        variants[variant]["image_changed_members"] = sum(row["changed"] for row in image_groups[variant])
        policy = data["static_checks"]["policy"]
        save(variant + "/static-policy.json", load(package / policy["source"]))
        receipt = data["paired_build_receipt"]
        save(variant + "/paired-receipt.json", load(package / receipt["source"]))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["variant", "layer", "target", "operation", "baseline_sha256", "candidate_sha256"])
    writer.writeheader()
    writer.writerows(all_rows)
    (HERE / "increments.csv").write_text(output.getvalue())
    save("image-group.json", image_groups)
    save("source-provenance.json", dict(original_reviewed_sources=[dict(path=PRIOR / variant / "reviewed-composition.json", sha256=sha(PRIOR / variant / "reviewed-composition.json")) for variant in variants],
        exact_candidate_native_manifest=variants["common"]["native_manifest_sha256"], exact_candidate_native_inputs=variants["common"]["native_inputs_sha256"],
        arming_correspondence=load(HERE / "base-identities.json")["source"], arming_correspondence_sha256=load(HERE / "base-identities.json")["source_sha256"],
        artifacts_rebuilt=False, image_rebaked=False, original_sources_and_build_receipts_remain_persistent=True))
    commands = gates["records"] + load(HERE / "native-delta-gates.json")["records"]
    if (HERE / "validation-runs.json").exists():
        commands += load(HERE / "validation-runs.json")
    save("results.json", dict(variants=variants, commands=commands, comparison="planned post-U13 per-board content, not promotion attestation",
        fresh_executor_status={variant: load(HERE / variant / "evidence/executor.json")["status"] for variant in variants},
        image_gates={variant: load(HERE / variant / "evidence/image-gates.json") for variant in variants},
        production_gates_passed=False, execution_enabled=False, promotion_confirmed=False, window_authorized=False,
        device_access=False, lock_taken=False, vm_used=False, active_tables_written=False,
        pending="outer fresh oatdump/G2 replay and signed actual armed/unarmed promotion correspondence; change only matching BASE parameters"))
    lines = ["# Exact fresh Mac command exits", "", "This is a disabled diagnostic. Independent component checks are not a complete executor PASS.", "",
        "| Evidence | Exit |", "|---|---:|"]
    lines += ["| `" + row["evidence"].split("/")[-1] + "` | " + str(row["exit_code"]) + " |" for row in commands]
    (HERE / "gate-exits.md").write_text("\n".join(lines) + "\n")
    paths = sorted(str(path.relative_to(REPO)) for path in HERE.rglob("*") if path.is_file() and ".artifacts" not in path.parts and "__pycache__" not in path.parts
        and path.name not in ["landing-paths.txt", "listing-receipt.json"])
    paths += [str(path.relative_to(REPO)) for path in (REPO / "specs/u14-on-u13-base").glob("*.spec.md")]
    paths += ["tools/spec-checks/tests/u14_on_u13_base.rs", str((HERE / "listing-receipt.json").relative_to(REPO))]
    paths = sorted(set(paths))
    (HERE / "landing-paths.txt").write_text("\n".join(paths) + "\n")
    save("listing-receipt.json", dict(paths=len(paths), sha256=sha(HERE / "landing-paths.txt"), execution_enabled=False))
    print("U14 per-board U13 preparation: disabled; metadata-only; landing=" + str(len(paths)))


if __name__ == "__main__":
    main()
