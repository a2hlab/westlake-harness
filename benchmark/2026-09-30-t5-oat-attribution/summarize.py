#!/usr/bin/env python3
"""Produce a portable handoff from locally captured OAT/source/native evidence."""
import csv
import json
import os
from pathlib import Path
import subprocess

from compare_oat import sha

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
SOURCE = WS / "westlake-harness-bms-deploy/bms/src/.work/b6-art14-recovery/art-r1"


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    report = json.loads((HERE / "t5-comparison.json").read_text())
    primary = next(x for x in report["segments"] if x["name"] == "boot.oat")
    manifest = WS / "_hw248-t5/SHA256SUMS"
    delivered = []
    for line in manifest.read_text().splitlines():
        expected, name = line.split()
        name = Path(name).name
        actual = sha((manifest.parent / "arm64" / name).read_bytes())
        if expected != actual:
            raise ValueError(f"delivery SHA mismatch: {name}")
        delivered.append(dict(name=name, sha256=actual))
    if len(delivered) != 27 or len(set(x["name"] for x in delivered)) != 27:
        raise ValueError("delivery must contain exactly 27 unique artifacts")
    write("candidate-receipt.json", dict(manifest_sha256=sha(manifest.read_bytes()), files=delivered))
    ranges = {
        "runtime/oat.h": [(141, 160)],
        "runtime/oat.cc": [(439, 468)],
        "dex2oat/dex2oat.cc": [(963, 976), (1625, 1662), (1703, 1725)],
        "dex2oat/linker/oat_writer.cc": [(116, 135), (2703, 2713), (3831, 3844), (3850, 3925)],
        "runtime/image.h": [(450, 491)],
        "runtime/gc/space/image_space.cc": [(3433, 3452)],
        "build/art.go": [(38, 87), (94, 116)],
        "runtime/read_barrier_config.h": [(28, 42), (74, 94)],
        "runtime/read_barrier-inl.h": [(35, 45), (72, 103)],
        "runtime/runtime_globals.h": [(43, 68)],
        "runtime/gc/collector_type.h": [(26, 40), (67, 78)],
        "cmdline/cmdline_types.h": [(537, 558)],
        "runtime/heap_poisoning.h": [(22, 37)],
        "runtime/mirror/object_reference.h": [(100, 106), (167, 180)],
        "runtime/gc/collector/mark_compact.cc": [(153, 169), (256, 277), (4220, 4227)],
        "runtime/native/dalvik_system_VMRuntime.cc": [(219, 224)],
        "libartbase/base/globals.h": [(52, 64)],
        "runtime/entrypoints/quick/quick_field_entrypoints.cc": [(418, 442)],
        "runtime/arch/arm64/quick_entrypoints_arm64.S": [(2528, 2540)],
        "compiler/optimizing/code_generator_arm64.cc": [(2135, 2165)],
    }
    source_evidence = {}
    for path, spans in ranges.items():
        file = SOURCE / path
        text = file.read_text().splitlines()
        source_evidence[path] = dict(path=str(file.relative_to(WS)), sha256=sha(file.read_bytes()),
                                    lines=[dict(line=i, text=text[i-1]) for start, end in spans
                                           for i in range(start, min(end, len(text)) + 1)])
    commit = subprocess.run(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    write("source-evidence.json", dict(commit=commit, files=source_evidence,
          note="Local clean r1 source identifies mechanisms; this is not a recovered d600 build command."))
    rows = []
    for segment in report["segments"]:
        a, b, d = segment["reference"], segment["candidate"], segment["comparison"]
        rows.append(dict(segment=segment["name"], reference_checksum=f'{a["header"]["checksum"]:08x}',
                         candidate_checksum=f'{b["header"]["checksum"]:08x}',
                         reference_kv_size=a["header"]["key_value_store_size"],
                         candidate_kv_size=b["header"]["key_value_store_size"],
                         text_size_delta=d["regions"]["text"]["candidate_size"]-d["regions"]["text"]["reference_size"],
                         text_differing_positions=d["regions"]["text"]["differing_positions"],
                         rodata_after_kv_differing_positions=d["regions"]["rodata_after_kv"]["differing_positions"],
                         dex_records_equal=d["dex_records_equal_ignoring_position"]))
    with (HERE / "residuals.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    flags = []
    def flag(name, value, level, evidence, setting, caveat=""):
        flags.append(dict(flag=name, reference_value=value, status=level, evidence=evidence,
                          t3b_setting=setting, caveat=caveat))
    flag("effective_read_barrier", False, "verified",
         "boot.oat kv concurrent-copying=false; libart ValidateOatFile VA 0x461bb4 calls IsConcurrentCopying, 0x461bb8 tbnz rejects true",
         "ART_USE_READ_BARRIER=false", "The KV alone measures compiler runtime state, not the original environment spelling; native evidence corroborates false.")
    flag("read_barrier_type", "none in active compiled paths", "verified",
         "artReadBarrierSlow VA 0x810f60 is ldr w0,[x1,w2,uxtw];ret; root slow is ldr;ret; inline cache has no Baker marking guard. read_barrier-inl.h:35-103",
         "ART_READ_BARRIER_TYPE not needed when ART_USE_READ_BARRIER=false", "Original ignored environment value cannot be recovered; do not claim BAKER or TABLELOOKUP.")
    flag("default_collector", "CMS (enum 2)", "verified",
         "XGcOption default allocator VA 0x76e5a4 mov w8,#2;0x76e5b8 str w8,[x0]; empty parse VA 0x770e50 matches; collector_type.h:26-40,67-78",
         "ART_DEFAULT_GC_TYPE=CMS", "Default is proven; live per-process -Xgc override was not inspected.")
    flag("generational_cc_default", False, "verified",
         "XGcOption default VA 0x76e5ac/0x76e5b4 zero bytes +4..15 including generational_cc at +6; cmdline_types.h:540-544; runtime_globals.h:43-60",
         "ART_USE_GENERATIONAL_CC=false", "A runtime option can override the default; collector implementations existing as symbols prove no selection.")
    flag("heap_poisoning", False, "verified",
         "MarkCompact::IsNullOrMarkedHeapReference VA 0x68e368 directly loads w1 then passes to IsMarked at 0x68e374 without negation; artReadBarrierSlow also loads directly; object_reference.h:100-106,170-179",
         "ART_HEAP_POISONING=false")
    flag("native_debug_build", False, "verified",
         "VMRuntime_vmLibrary VA 0x3db6bc uses string at VA/file offset 0x21be56 = libart.so; dalvik_system_VMRuntime.cc:221-223 selects it by kIsDebugBuild; default GC verification bytes also zero",
         "Select release dex2oat64/libart.so (not dex2oatd64/libartd.so); NDEBUG supplied by build target",
         "OAT debuggable=false by itself would not prove a release libart.")
    flag("test_debug_gc_override", False, "derived",
         "CMS default verified; build/art.go:44-47 ART_TEST_DEBUG_GC=true forces SS and TLAB",
         "ART_TEST_DEBUG_GC=false")
    flag("tlab_build_default", "unknown (r1 flags imply false for rb-off/CMS)", "unknown",
         "build/art.go:41,48,78-84 derives TLAB; actual R155 caller value not recovered",
         "No direct ART_USE_TLAB env knob in r1 globalFlags; inspect compiler flags", "Do not equate available TLAB code with enabled TLAB.")
    flag("cxx_interpreter", "unknown", "unknown", "build/art.go:55-57; no definitive native predicate extracted", "Record effective ART_USE_CXX_INTERPRETER; do not guess")
    flag("sanitizers_and_stack_overflow_gap", "unknown", "unknown", "build/art.go:94-116 ties gaps to sanitizer config; no original compile receipt", "Archive sanitizer/ART_STACK_OVERFLOW_GAP flags; do not infer from missing symbols")
    flag("optimization_level", "unknown", "unknown", "build/art.go:38-39 defaults ART_NDEBUG_OPT_FLAG to -O3; original receipt absent", "Record actual ART_NDEBUG_OPT_FLAG; upstream default is not R155 evidence")
    flag("aot_java_debuggable", False, "verified", "reference boot.oat KV debuggable=false", "Do not add --debuggable")
    flag("aot_native_debuggable", False, "verified", "reference boot.oat KV native-debuggable=false", "Do not add --generate-debug-info solely to match metadata")
    flag("aot_compiler_filter", "speed", "verified", "reference boot.oat KV compiler-filter=speed", "--compiler-filter=speed")
    flag("isa_features_bitmap", "0x3", "verified", "reference and T5 OAT230 header +16 both 3; ISA at +12 both 2=arm64", "Keep instruction-set arm64 and verify generated bitmap 0x3")
    flag("main_image_metadata", "8 keys; no bootclasspath-checksums or compilation-reason", "verified", "reference OAT@0x1000 KV@0x1044 size2259; T5 actual also 8 keys", "Do not add these keys; omit --compilation-reason for reference reproduction")
    write("build-flags.json", dict(libart_sha256="59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f", flags=flags))
    with (HERE / "build-flags.csv").open("w", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=list(flags[0])); writer.writeheader(); writer.writerows(flags)
    write("results.json", dict(status="offline_attribution_complete", reference_boot_sha=primary["reference"]["sha256"],
          candidate_boot_sha=primary["candidate"]["sha256"], candidate_checksum=f'{primary["candidate"]["header"]["checksum"]:08x}',
          earlier_reported_checksum="31a3e81e", earlier_artifact_available=False,
          l1_equal=sum(x["equal"] is True for x in report["images"]), total=27, vdex_equal=9,
          text_different=9, metadata_only=False, dex_locations_and_input_checksums_equal=True,
          per_file_dex_records_equal=sum(x["comparison"]["dex_records_equal_ignoring_position"] for x in report["segments"]),
          image_oat_pair_consistent=all(x["candidate_consistent"] and x["reference_consistent"] for x in report["image_oat_checksum_pairs"]),
          flags_verified=sum(x["status"]=="verified" for x in flags), flags_derived=sum(x["status"]=="derived" for x in flags),
          flags_unknown=sum(x["status"]=="unknown" for x in flags),
          runtime_validation="unverified", screenshots=None, alive=None,
          boundary="T3b build and T6 device evidence belong to other lanes; no original d600 build environment was recovered."))


if __name__ == "__main__":
    main()
