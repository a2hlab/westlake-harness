"""Preserve donor sources, classify raw deltas and check actual package consumers."""
import ast
import json
import re
import shutil
import sys

from common import BASE, HERE, MASTER, PACKAGE, REPO, WORKSPACES, capture, portable, save, sha
import generation_bundle as gb
import generation_static_checks as static


def main():
    old, new = static.effective(BASE), static.effective(PACKAGE)
    consumers = {}
    for row in new.values():
        source = gb.member(PACKAGE, row)
        if source.read_bytes()[:4] == b"\x7fELF":
            consumers.setdefault(row["sha256"], source)
    checks = []
    for name in ["libbionic_compat.so", "libnativeloader.so", "liboh_android_runtime.so"]:
        target = "/system/android/lib64/" + name
        command = [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", gb.member(BASE, old[target]), "--new", gb.member(PACKAGE, new[target]), "--calls", "--json", HERE / "evidence" / ("consumer-" + name + ".json")]
        for source in consumers.values():
            command.extend(["--consumer", source])
        checks.append(dict(target=target, consumer_count=len(consumers), result=capture("consumer-" + name, command)))
    save("consumer-checks.json", dict(scope="All unique effective U13 package ELFs, not a claim of every APK or relocation scope", unique_consumers=len(consumers), checks=checks))
    for name, root in [("u12", BASE), ("u13", PACKAGE)]:
        capture("dlext-body-" + name, ["llvm-objdump", "-d", "--disassemble-symbols=android_dlopen_ext", gb.member(root, (old if name == "u12" else new)["/system/android/lib64/libbionic_compat.so"])])
    runtime_dir = MASTER / "benchmark/2026-10-02-m1-session-slots/runtime"
    single_dir = REPO / "benchmark/2026-10-02-u13-single-native"
    vlc_dir = REPO / "benchmark/2026-10-02-u12-vlc-bionic-residue"
    snapshots = [runtime_dir / "runtime-build-receipt-u13.json", runtime_dir / "README.md", runtime_dir / "acceptance.py", runtime_dir / "acceptance.txt", runtime_dir / "build_runtime_u13.py", MASTER / "benchmark/2026-10-02-getlongfield-null/patch/asset_manager.cpp.patch", vlc_dir / "build-receipt.json", vlc_dir / "persistent-inventory.json", vlc_dir / "build.py", single_dir / "policy-build-receipt.json", single_dir / "source-identity.json", single_dir / "policy.patch"]
    archive = []
    for index, source in enumerate(snapshots):
        target = HERE / "provenance" / (str(index) + "-" + source.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(portable(source.read_text()))
        archive.append(dict(original=source, original_sha256=sha(source), snapshot=target, snapshot_sha256=sha(target)))
    scan = json.loads((PACKAGE / "native/native-checks/scan-manifest.json").read_text())
    for name in scan["sources"]:
        if name.startswith("u13-") or name == "u10-1-native-policy.h":
            source = PACKAGE / "native/native-checks" / name
            target = HERE / "sources" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            archive.append(dict(original=source, original_sha256=sha(source), snapshot=target, snapshot_sha256=sha(target)))
    runtime_original = WORKSPACES / "westlake-harness-bms-deploy/benchmark/2026-09-30-n2-native/src/android_graphics_compat_shim.cpp"
    original_text = runtime_original.read_text()
    candidate_text = (runtime_dir / "src/android_graphics_compat_shim.cpp").read_text()
    n1_comparisons = []
    for text in ['s_bridgeHandle = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);', 'void* h = android::dlopen("libEGL.so", RTLD_NOW | RTLD_NOLOAD);']:
        before = [(index, line) for index, line in enumerate(original_text.splitlines(), 1) if text in line]
        after = [(index, line) for index, line in enumerate(candidate_text.splitlines(), 1) if text in line]
        n1_comparisons.append(dict(text=text, baseline=before, candidate=after, unchanged_statement=bool(before and after)))
    save("new-n1-lineage.json", dict(comparisons=n1_comparisons, baseline_source=runtime_original, baseline_source_sha256=sha(runtime_original), candidate_source_sha256=sha(runtime_dir / "src/android_graphics_compat_shim.cpp"), interpretation="Two newly covered N1 source sites, not new ELF open sites. Both exact NOLOAD statements already occur in the baseline gfx source; unresolved runtime availability remains outer review, not successful resident-handle proof"))
    raw = (HERE / "evidence/strings-liboh_android_runtime.so-root.txt").read_text()
    rows = []
    for line in raw.splitlines():
        if line.startswith(("ADDED", "DROPPED")):
            value = ast.literal_eval(line[8:])
            marker = value.startswith("[M1-COPY]")
            label = re.match(r"\[\s*([0-9a-f]+)\] row ", value)
            kind = "M1 cross-copy diagnostic" if marker else "readelf offset embedded in printable output" if label else "printable rendering of relative jump-table data"
            rows.append(dict(operation=line.split()[0], value=value, length=len(value), classification=kind, review="allow proposed, outer not yet signed", source="sources/u13-m1-compat-shim.cpp" if marker else "provenance/1-README.md:120", rationale="Single M1 diagnostic, no new loader operation" if marker else "0x1c6e1 -> 0x1c73e, delta0x5d equals92-byte marker+NUL" if label else "Raw rodata bytes change with relink; donor explains relative offsets and equal-length twins (373 and70). Not treated as removed policy text"))
    save("strings-review.json", dict(runtime=dict(raw_exit_code=1, dropped=3, added=4, rows=rows, evidence="evidence/strings-liboh_android_runtime.so-root.txt"), policy=dict(raw_exit_code=1, dropped=0, added=["libmedia_jni.so", "/system/android/lib64/liboh_android_runtime.so"], rationale="Exact reviewed resident-only media alias on existing runtime; SoundPool and mediandk unchanged", evidence="evidence/strings-libnativeloader.so-root.txt"), compat=dict(raw_exit_code=0, dropped=0, added=0), approved_by=None, execution_enabled=False))
    full = json.loads((HERE / "full-package-open-sites.json").read_text())
    for digest, row in full["scans"].items():
        source = HERE / ".artifacts/full-scans" / (digest + ".json")
        target = HERE / "scans" / (digest + ".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(portable(source.read_text()))
        row.update(public_json=portable(target), public_json_sha256=sha(target))
    save("full-package-open-sites.json", full)
    save("provenance-index.json", dict(files=archive, source_rebuilds_performed=0, copied_donors_only=True))
    for name, source in [("native-manifest.json", PACKAGE / "native/package.json"), ("bundle-manifest.json", PACKAGE / "bundle.json"), ("scan-manifest.json", PACKAGE / "native/native-checks/scan-manifest.json")]:
        target = HERE / "manifests" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    save("static-delta-explanation.json", dict(compat=dict(raw_added=1, raw_removed=1, open_count_before=2, open_count_after=2, reason="Only unresolved-clobber diagnostic PC changes from0x3758 to0x3a58; named calls unchanged, same tail dlopen site. Raw production signature remains REVIEW_REQUIRED for both aliases", evidence=["evidence/dlext-body-u12.txt", "evidence/dlext-body-u13.txt", "evidence/abi-libbionic_compat.so-root.json"], delta_sha256="45e215dd7193957e17d99b67e20b416dfaa6047f77225a927bab483afae12608"), runtime=dict(open_count_before=197, open_count_after=197, findings_before=198, findings_after=198, raw_added=0, raw_removed=0, namespace_edges=0, note="Donor's 198 count is findings, not open sites; this full scan counts197 sites and198 findings"), policy=dict(open_count_before=0, open_count_after=0, namespace_edges=0), host=dict(unchanged=True, open_sites=8, namespace_edges=17, inherit_repeat=0, inherit_after_open=4, reason="U12 host copied exactly; all four existing syntactic may-path findings retain bytes, PCs and behavior, no N11h host was stacked"), approved_by=None))
    print(json.dumps(dict(consumer_count=len(consumers), consumer_exit_codes=[row["result"]["exit_code"] for row in checks], provenance_files=len(archive), full_scan_evidence=len(full["scans"])), indent=2))


if __name__ == "__main__":
    main()
