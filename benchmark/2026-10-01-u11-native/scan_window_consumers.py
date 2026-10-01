import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import zipfile


HERE = Path(__file__).resolve().parent
LOCK_APIS = {"ANativeWindow_lock", "ANativeWindow_unlockAndPost"}
MISSING_INLINE = "_ZN7_JNIEnv16CallObjectMethodEP8_jobjectP10_jmethodIDz"


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def symbols(filename, defined):
    command = ["llvm-nm", "-D", "--defined-only" if defined else "--undefined-only",
               "--format=just-symbols", str(filename)]
    return {value.split("@")[0] for value in subprocess.check_output(command, text=True).split()}


def dynamic(filename):
    output = subprocess.check_output(["llvm-readelf", "-d", str(filename)], text=True)
    return {"needed": re.findall(r"\(NEEDED\).*?\[([^]]+)\]", output),
            "soname": re.findall(r"\(SONAME\).*?\[([^]]+)\]", output)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspaces", type=Path, default=os.environ.get("WORKSPACES", HERE.parents[2]))
    parser.add_argument("--build-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    workspaces = args.workspaces.resolve()
    baseline = workspaces / "westlake-generation-u9-j10g-238ffc14/native/payload/android/lib64"
    old = baseline / "libandroid.so"
    runtime = baseline / "liboh_android_runtime.so"
    candidate = args.build_dir / "libandroid.so"
    if digest(old) != "9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db" or digest(runtime) != "ac59dec077195bc7678c712505b0d802c56e07edea8d049be4a188d20485b7bf":
        raise ValueError("baseline owner identity mismatch")
    old_exports = symbols(old, True)
    runtime_exports = symbols(runtime, True)
    candidate_exports = symbols(candidate, True)
    if candidate_exports != LOCK_APIS:
        raise ValueError("shim must define exactly the lock pair")
    missing = sorted(old_exports - (runtime_exports | candidate_exports))
    manifests = [HERE.parents[1] / "benchmark/2026-10-01-u7-prospective/v1/apps-u7.json",
                 workspaces / "westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json"]
    applications = [entry for filename in manifests for entry in json.loads(filename.read_text())["apps"]]
    if len(applications) != 166 or len({entry["key"] for entry in applications}) != 166:
        raise ValueError("expected 166 unique APK identities")
    args.out.mkdir(parents=True, exist_ok=True)
    selected = []
    rows = []
    zero_native = []
    input_inventories = []
    archive_count = 0
    for application in applications:
        key = application["key"]
        candidates = [Path(os.path.expandvars(application["apk"]))] if "apk" in application else list((Path.home() / "a2hlab/app-inputs" / key).glob("*.apk"))
        apk = next((filename for filename in candidates if filename.is_file() and digest(filename) == application["apk_sha256"]), None)
        if apk is None:
            raise ValueError("APK identity missing: " + key)
        count = 0
        archive_candidates = [apk]
        inventory_file = apk.parent / "app-input.json"
        if inventory_file.is_file():
            inventory = json.loads(inventory_file.read_text())
            extra = []
            for entry in inventory.get("splits", {}).values():
                split = apk.parent / entry["staged"]
                if split.parent != apk.parent or not split.is_file() or digest(split) != entry["sha256"]:
                    raise ValueError("split identity mismatch: " + key + ":" + entry["staged"])
                archive_candidates.append(split)
                extra.append({"archive": split.name, "sha256": entry["sha256"]})
            input_inventories.append({"key": key, "inventory_sha256": digest(inventory_file),
                                      "inventory_base_sha_matches": inventory.get("apk_sha256") == application["apk_sha256"],
                                      "splits": extra})
        for archive_file in archive_candidates:
            archive_count += 1
            archive_sha = digest(archive_file)
            with zipfile.ZipFile(archive_file) as archive:
                for member in sorted(archive.namelist()):
                    if not member.startswith("lib/arm64-v8a/") or not member.endswith(".so"):
                        continue
                    content = archive.read(member)
                    if content[:6] != b"\x7fELF\x02\x01" or int.from_bytes(content[18:20], "little") != 183:
                        continue
                    count += 1
                    extracted = args.out / "consumers" / key / archive_file.name / Path(member).name
                    extracted.parent.mkdir(parents=True, exist_ok=True)
                    extracted.write_bytes(content)
                    dependencies = dynamic(extracted)["needed"]
                    imported = symbols(extracted, False)
                    lock = sorted(imported & LOCK_APIS)
                    needs_android = "libandroid.so" in dependencies
                    row = {"key": key, "apk_sha256": application["apk_sha256"], "member": member,
                           "archive": archive_file.name, "archive_sha256": archive_sha,
                           "sha256": hashlib.sha256(content).hexdigest(), "needed": dependencies,
                           "lock_imports": lock, "needed_libandroid": needs_android,
                           "missing_inline_imported": MISSING_INLINE in imported}
                    rows.append(row)
                    if lock or needs_android:
                        selected.append({**row, "old_exports_consumed": sorted(imported & old_exports),
                                         "unresolved_after_owner_route": sorted((imported & old_exports) - (runtime_exports | candidate_exports))})
        if count == 0:
            zero_native.append(key)
    tool = workspaces / "westlake-harness/scripts/lab/abi_diff.py"
    consumers = [argument for row in selected for argument in ["--consumer", str(args.out / "consumers" / row["key"] / row["archive"] / Path(row["member"]).name)]]
    tool_reports = []
    for name, new in [("old-root-to-runtime", runtime), ("old-root-to-shim", candidate)]:
        target = args.out / (name + "-abi.json")
        command = ["python3", str(tool), "--old", str(old), "--new", str(new), "--calls", "--json", str(target), *consumers]
        run = subprocess.run(command, capture_output=True, text=True)
        if run.returncode not in [0, 1] or not target.is_file():
            raise ValueError("ABI tool execution failed: " + run.stderr)
        report = json.loads(target.read_text())
        raw_sha = digest(target)
        text = target.read_text().replace(str(args.out.resolve()), "$SCAN_OUT").replace(str(args.out), "$SCAN_OUT")
        target.write_text(text)
        tool_reports.append({"file": target.name, "exit": run.returncode, "raw_report_sha256": raw_sha,
                             "path_normalization": "scan output prefix only; no counts, differences or failure rows changed",
                             "consumer_breaks": len(report["consumer_breaks"]), "call_differences": len(report["call_diffs"]),
                             "meaning": "individual ELF report, not the union-owner gate; retain removals and differences unfiltered"})
    lock_rows = [row for row in selected if row["lock_imports"]]
    report = {"schema": "u11-root-libandroid-consumers-v1", "scanned_APK_keys": 166,
              "scanned_native_members": len(rows), "zero_native_keys": zero_native,
              "scanned_archives": archive_count, "input_inventory_bindings": input_inventories,
              "baseline_root_sha256": digest(old), "runtime_sha256": digest(runtime), "candidate_sha256": digest(candidate),
              "old_export_count": len(old_exports), "runtime_export_count": len(runtime_exports),
              "candidate_export_count": len(candidate_exports), "candidate_dynamic": dynamic(candidate),
              "missing_superset_exports": missing, "missing_export_approval": "pending outer; never implicitly approved",
              "lock_consumer_keys": len({row["key"] for row in lock_rows}), "lock_consumer_members": len(lock_rows),
              "needed_libandroid_keys": len({row["key"] for row in selected if row["needed_libandroid"]}),
              "needed_libandroid_members": sum(row["needed_libandroid"] for row in selected),
              "selected_consumers": selected, "all_native_members": rows,
              "union_owner_consumer_breaks": [row for row in selected if row["unresolved_after_owner_route"]],
              "missing_inline_consumers_all_APK_members": [row for row in rows if row["missing_inline_imported"]],
              "canonical_abi_tool_sha256": digest(tool), "canonical_abi_reports": tool_reports,
              "limits": "All ELF64 AArch64 native members of 166 SHA-pinned base APKs plus individually SHA-pinned split archives from current local input inventories; direct .so sidecar substitutions, runtime inventory binding, namespace visibility and live owner counts remain assembly/target gates",
              "single_owner_maps": "not measured; no board access. Final owner-route assertion must reject root9ccf64f8 mapping and duplicate runtime SONAME/mappings"}
    (args.out / "consumers.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ["scanned_APK_keys", "scanned_native_members", "lock_consumer_keys", "lock_consumer_members", "needed_libandroid_keys", "needed_libandroid_members", "missing_superset_exports", "union_owner_consumer_breaks"]}))


if __name__ == "__main__":
    main()
