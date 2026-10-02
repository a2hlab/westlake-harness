import json

from common import HERE, REPO, save, sha


def main():
    composition = json.loads((HERE / "composition.json").read_text())
    summary = json.loads((HERE / "report-summary.json").read_text())
    save("results.json", dict(composition=composition, gates=summary, device_access=False, execution_enabled=False,
        promotion=False, fresh_outer_production_required=True, new_metadata_authorization_required=True))
    save("binding-map.json", dict(rows=[
        dict(kind="effective baseline evidence", old_sha256=composition["original_base_bundle_sha256"], new_sha256=composition["base_bundle_sha256"]),
        dict(kind="U13 metadata only", old_sha256=composition["original_package_bundle_sha256"], new_sha256=composition["bundle_sha256"])],
        native_manifest_unchanged=True, inputs_unchanged=True, registry_delta=[], new_native_admission_delta=[],
        status="outer approved metadata preparation; renewed window authorization pending"))
    save("documentation.json", dict(layout_row="| **`benchmark/2026-10-03-u13-61b-effective-base/`** | **61b-local installation identity references, unchanged U13 outputs, exact signed full maps and fresh outer production replay.** |",
        digest_line="- 61b U13基座(2026-10-03,cx-bms):libinstalls两处51e已签且不在native库存；prepare却让candidate reference/runtime.txt覆盖baseline-native成2c，整图316必须对每板签认，不能仅static.effective/短指纹。本地b79原件51e核SHA，61b变体只换两引用+BASE绑定，native85ae/c40f及输出不变；baseline=expected51e且0服务动作，原912不改。见benchmark/2026-10-03-u13-61b-effective-base/。",
        runbook_line="- For board-specific platform service differences, inspect executor.prepare's full baseline/expected maps: candidate runtime reference values override baseline-native. Use a metadata-only board-specific effective BASE and candidate reference, require exact signed full-map equality and no service action, and replay production on both surfaces before reauthorization."))
    paths = sorted(path.relative_to(REPO).as_posix() for path in HERE.rglob("*") if path.is_file()
        and not any(part in [".artifacts", "__pycache__"] for part in path.parts)
        and path.name not in ["landing-paths.txt", "preflight.txt", "listing-receipt.json"])
    paths += ["specs/u13-61b-effective-base/project.spec.md", "specs/u13-61b-effective-base/t1-bind.spec.md", "tools/spec-checks/tests/u13_61b_effective_base.rs"]
    landing = HERE / "landing-paths.txt"
    landing.write_text("\n".join(sorted(paths)) + "\n")
    save("listing-receipt.json", dict(listing_sha256=sha(landing), count=len(paths), execution_enabled=False))
    print("landing=" + str(len(paths)) + " sha256=" + sha(landing))


if __name__ == "__main__":
    main()
