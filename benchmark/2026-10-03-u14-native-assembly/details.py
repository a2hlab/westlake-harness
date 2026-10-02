import ast
import importlib.util
import json
from pathlib import Path
import re
import sys

from common import ASSEMBLY_BASE, BRIDGE, DONOR, HERE, INTERMEDIATE, MASTER, REPEAT, WS, capture, expand, portable, save, sha


def main():
    composition = json.loads((HERE / "composition.json").read_text())
    package = expand(composition["package"])
    old = ASSEMBLY_BASE / "native/payload/android/lib64/liboh_adapter_bridge.so"
    candidate = package / "native/payload/android/lib64/liboh_adapter_bridge.so"
    module_path = MASTER / "benchmark/2026-10-02-u14-bridge-r1r3/equiv.py"
    spec = importlib.util.spec_from_file_location("bridge_equiv", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = []
    literals = []
    for label, path in [("846", old), ("e34", INTERMEDIATE), ("7daa", candidate)]:
        records.append(capture("preload-" + label, ["llvm-objdump", "-d", "--no-show-raw-insn",
            "--disassemble-symbols=_ZL22preload_libmali_globalv", path]))
        text = (HERE / ".artifacts/raw" / ("preload-" + label + ".txt")).read_text()
        match = re.search(r"([0-9a-f]+):\s+adr\s+x0,\s+0x([0-9a-f]+)", text)
        call = re.search(r"([0-9a-f]+):\s+bl\s+.*<dlopen@plt>", text)
        if not match or not call or "mov\tw1, #0x102" not in text:
            raise ValueError("Preload instruction identity unknown")
        address = int(match[2], 16)
        literal = module.Image(str(path)).cstr(address)
        if literal != "libmali.so.0":
            raise ValueError("Preload ADR does not resolve to the same literal")
        literals.append(dict(label=label, sha256=sha(path), adr_pc="0x" + match[1], literal_address=hex(address),
            call_pc="0x" + call[1], literal=literal, flags=0x102, namespace="caller-default"))
    delta = json.loads((HERE / "open-delta.json").read_text())["delta"]
    save("adr-proof.json", dict(rows=literals, diagnostic_only=True, scanner_output_unchanged=True,
        independent_tool=str(module_path), tool_sha256=sha(module_path), records=records,
        scope="One preload call only; not a claim of whole-library equivalence"))
    static_report = json.loads((HERE / "evidence/static-vs-u13.json").read_text())
    bridge_member = next(row for row in static_report["members"] if row["target"].endswith("/liboh_adapter_bridge.so"))
    save("static-allowance-draft.json", dict(execution_enabled=False, applied=False, approved_by=None,
        entry={name: bridge_member[name] for name in ["target", "candidate_sha256", "deployed_sha256", "delta_sha256"]},
        delta=bridge_member["open_site_delta"], evidence=["benchmark/2026-10-03-u14-native-assembly/adr-proof.json",
            "benchmark/2026-10-03-u14-native-assembly/evidence/open-candidate.txt"],
        reason="ADR diagnostic displacement only; independently resolves libmali.so.0 with unchanged flags and namespace"))
    sources = DONOR / "src/bms/src/adapter"
    source_paths = []
    for group in ["core", "activity", "window", "surface", "broadcast", "contentprovider"]:
        directory = DONOR / "window-jni" if group == "window" else sources / "framework" / group / "jni"
        source_paths += [path for path in sorted(directory.glob("*.cpp")) if "-untested-on-" not in path.name and path.name != "display_manager_adapter_jni.cpp"]
    source_paths += [sources / "framework/window/jni/display_manager_adapter_jni.cpp",
        WS / "westlake-inputs/sources/fn03-core-846-recon-v1/fn03_lifecycle_core.cpp"]
    driver = sources / "build/inner/compile_oh_adapter_bridge_arm64.sh"
    source_paths += [sources / match for match in re.findall(r'"\$ADAPTER_ROOT/(framework/package-manager/[^" ]+)"', driver.read_text())]
    source_paths.append(sources / "framework/native-compat/jni-attach-admission/src/jni_attach_admission.cpp")
    if len(source_paths) != 50 or len(set(source_paths)) != 50:
        raise ValueError("Compile source closure drift")
    closure = []
    for path in source_paths:
        stem = path.name.removesuffix(".cpp")
        object_path = DONOR / "obj" / (path.parent.parent.name + "__" + stem + ".o")
        closure.append(dict(path=path, sha256=sha(path), object=object_path, object_sha256=sha(object_path)))
    snapshots = []
    for source in [MASTER / "benchmark/2026-10-03-u14-bridge-m5-m6/build_m5m6.sh",
        MASTER / "benchmark/2026-10-02-u14-bridge-r1r3/build_r1r3.sh",
        MASTER / "benchmark/2026-10-02-u14-bridge-baseline/build_u14_bridge.sh", driver]:
        output = HERE / "inputs/recipes" / source.name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(portable(source.read_text()))
        snapshots.append(dict(original=source, original_sha256=sha(source), snapshot=output.relative_to(HERE).as_posix(), snapshot_sha256=sha(output)))
    patch_root = MASTER / "benchmark/2026-10-02-u14-bridge-r1r3/patches"
    for name in ["win-r1-focus-bridge.patch", "win-r2-root-blast.patch", "win-r3-rs-node-holder.patch", "win-m5-dialog-zlevel.patch", "adapter-m6-finishing-background.patch"]:
        source = patch_root / name
        output = HERE / "inputs/patches" / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(source.read_bytes())
        snapshots.append(dict(original=source, original_sha256=sha(source), snapshot=output.relative_to(HERE).as_posix(), snapshot_sha256=sha(output)))
    build_logs = []
    for label, donor in [("a", DONOR), ("b", REPEAT)]:
        if sha(donor / "out/liboh_adapter_bridge.so") != BRIDGE:
            raise ValueError("Donor repeat mismatch")
        for source in sorted((donor / "logs").glob("*.log")):
            output = HERE / "evidence" / ("donor-" + label + "-" + source.name)
            output.write_text(portable(source.read_text()))
            build_logs.append(dict(original=source, original_sha256=sha(source), snapshot=output.relative_to(HERE).as_posix(), snapshot_sha256=sha(output)))
    sdk = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native")
    tools = [dict(path=sdk / "llvm/bin" / name, sha256=sha(sdk / "llvm/bin" / name)) for name in ["clang", "clang++", "ld.lld", "llvm-ar"]]
    save("provenance.json", dict(source_commit=(DONOR / "src/COMMIT").read_text().strip(), sources=closure, source_count=50,
        persistent_source_root=DONOR, snapshots=snapshots, build_logs=build_logs, two_donor_artifacts_same_bytes=True,
        artifact_sha256=BRIDGE, observed_recipe_tools=tools, historical_tool_hashes="not independently recorded by donor log; current recipe-path tools observed read-only",
        local_rebuild=False, vm_used=False, recipe_driver_sha256=sha(driver)))
    source_texts = {str(path.relative_to(DONOR)) if path.is_relative_to(DONOR) else path.name: path.read_text(errors="replace") for path in source_paths}
    trace_header = sources / "framework/core/include/oh_br_trace.h"
    trace_snapshot = HERE / "inputs/oh_br_trace.h"
    trace_snapshot.write_bytes(trace_header.read_bytes())
    changes = []
    for label in ["846-to-e34", "e34-to-candidate", "846-to-candidate"]:
        raw = (HERE / "evidence" / ("strings-" + label + ".txt")).read_text()
        for line in raw.splitlines():
            if not line.startswith(("ADDED ", "DROPPED ")):
                continue
            operation, text = line.split(maxsplit=1)
            value = ast.literal_eval(text)
            matches = []
            for source_name, content in source_texts.items():
                for number, source_line in enumerate(content.splitlines(), 1):
                    if value in source_line:
                        matches.append(dict(source=source_name, line=number, text=source_line.strip()))
            if value.startswith("[IPC] %{public}s WARN pass-through BACKGROUND_NEW"):
                matches = [dict(source="inputs/u14-bridge-ability.cpp", line=217, text="OH_BR_IPC_WARN FGGUARD with adjacent concatenated format literals"),
                    dict(source="inputs/oh_br_trace.h", line=113, text='"[IPC] %{public}s WARN " fmt')]
            changes.append(dict(pair=label, operation=operation, value=value, source_matches=matches,
                classification="source-text" if matches else "read-only-layout-diagnostic-pending-review",
                approval=None, scope="inherited e34" if label == "846-to-e34" else "M5/M6" if label == "e34-to-candidate" else "whole selected bridge"))
    save("strings-review.json", dict(rows=changes, raw_outputs_preserved=True, approved=False,
        warning="Unmatched readelf printable runs are not auto-approved; review raw bytes/layout evidence"))
    current = json.loads((MASTER / "knowledge/gates/new-native-admissions.json").read_text())
    save("admissions-source.json", current, compact=True)
    old_manifest = sha(ASSEMBLY_BASE / "native/package.json")
    prior_rows = [row for row in current["admissions"] if row["package_manifest_sha256"] == old_manifest]
    if len(prior_rows) != 3:
        raise ValueError("Expected the three approved U13 objects")
    admissions = []
    for row in prior_rows:
        entry = dict(row)
        entry.update(package_manifest_sha256=composition["native_manifest_sha256"], approved_by=None,
            auto_from=dict(package_manifest_sha256=old_manifest, sha256=row["sha256"], target=row["target"]),
            reason="Same U13 object; U14 binding preview awaiting outer approval")
        admissions.append(entry)
    save("new-native-admissions-draft.json", dict(schema="westlake-new-native-admissions/v1", admissions=admissions,
        applied=False, execution_enabled=False, needed_only_if_transaction_baseline_lacks_objects=True))
    review = json.loads((HERE / "needs-outer-review.json").read_text())
    save("n1-review-summary.json", dict(total=len(review["new_findings"]), unknown=5, unresolved_calls=34,
        new_m6_lookups=[dict(method="findByOhToken", signature="(J)Landroid/os/IBinder;", source="inputs/u14-bridge-ability.cpp", line=163),
            dict(method="isDestroying", signature="(Landroid/os/IBinder;)Z", source="inputs/u14-bridge-ability.cpp", line=165)],
        inherited_unknowns=["nativeRegisterInputChannel_impl NOLOAD at input:72", "orientation GetStaticMethodID ability:471", "callJavaVoidMethod GetMethodID ability:335"],
        external_calls=[row["detail"] for row in review["new_findings"] if row["kind"] == "unresolved_calls"],
        warning="Coverage uncertainty is not 39 demonstrated regressions and is not zero findings; all await review"))
    inventory_path = WS / "westlake-harness-bms/benchmark/2026-10-02-toutiao-bionic-scope/consumers.json"
    inventory = json.loads(inventory_path.read_text())
    member_root = inventory_path.parent / ".artifacts/members"
    consumers = {member["sha256"]: member_root / (member["sha256"] + ".so")
        for app in inventory["apps"] for member in app["members"] if member["status"] == "ELF64-AArch64" and member["imports"]}
    for key in ["vlc", "fd-fennec_fdroid", "firefox", "ppsspp"]:
        for path in (WS / "westlake-harness-bms/benchmark/2026-10-02-u12-disappeared/.artifacts").glob(key + "-*.so"):
            consumers[sha(path)] = path
    if len(consumers) != 219 or any(sha(path) != digest for digest, path in consumers.items()):
        raise ValueError("Consumer inventory identity changed")
    abi_output = HERE / ".artifacts/abi-consumers.json"
    records.append(capture("abi-consumers", [sys.executable, MASTER / "scripts/lab/abi_diff.py", "--old", old, "--new", candidate,
        "--calls", "--json", abi_output, *[item for path in consumers.values() for item in ["--consumer", path]]]))
    save("evidence/abi-consumers.json", json.loads(abi_output.read_text()), compact=True)
    save("consumer-set.json", dict(count=219, files=[dict(path=path, sha256=digest) for digest, path in sorted(consumers.items())],
        scope="Import intersection against replaced bridge exports; not a namespace-resolution or app-gain proof"))
    records.append(capture("deployed-whois-transaction", [sys.executable, MASTER / "scripts/lab/deployed_whois.py",
        "liboh_adapter_bridge.so", "--generation", expand(composition["transaction_base"])]))
    save("details-summary.json", dict(adr_literal_same=True, source_count=50, donors_same=True, strings_rows=len(changes),
        static_delta_sha256=bridge_member["delta_sha256"], executed=records, execution_enabled=False))
    print("ADR old/e34/new -> libmali.so.0 flags0x102 caller-default; raw diagnostic delta preserved")
    print("PROVENANCE compiled sources50, donors a/b7daa identical, no local rebuild/no VM")
    print("STRINGS all raw rows retained for outer review; no blanket approval; consumer inventory219")


if __name__ == "__main__":
    main()
