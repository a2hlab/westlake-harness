#!/usr/bin/env python3
"""Generate the immutable, project-local Route A input ledger."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
PLUGIN = Path(__file__).resolve().parent
LOGICAL_GENERATION_ROOT = ROOT / ".work/product-tls-generation"
GENERATION_ROOT = Path(os.environ.get(
    "WESTLAKE_GENERATION_ROOT", LOGICAL_GENERATION_ROOT)).resolve()
LOGICAL_BIONIC_PROVIDER_ROOT = (
    ROOT / ".work/bionic-musl-provider/provider-inputs-v12-nobroadstub")
BIONIC_PROVIDER_ROOT = Path(os.environ.get(
    "WESTLAKE_BIONIC_PROVIDER_ORIGIN",
    LOGICAL_BIONIC_PROVIDER_ROOT)).resolve()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        generation_relative = resolved.relative_to(GENERATION_ROOT)
    except ValueError:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    return (Path(".work/product-tls-generation") /
            generation_relative).as_posix()


def generation_input(relative_path: str) -> Path:
    return GENERATION_ROOT / relative_path


def provenance_origin(origin_text: str) -> tuple[Path, Path]:
    logical = Path(origin_text)
    logical_product_prefix = Path(".work/product-tls-generation")
    logical_provider_prefix = Path(
        ".work/bionic-musl-provider/provider-inputs-v12-nobroadstub")
    try:
        suffix = logical.relative_to(logical_product_prefix)
    except ValueError:
        try:
            suffix = logical.relative_to(logical_provider_prefix)
        except ValueError:
            return (ROOT / logical).resolve(), ROOT.resolve()
        return ((BIONIC_PROVIDER_ROOT / suffix).resolve(),
                BIONIC_PROVIDER_ROOT)
    # Frozen provider provenance names the historical product closure that
    # supplied those checked-in libraries.  It must not be rebound to an
    # isolated generation under test: current generation inputs are already
    # represented explicitly by frozen.sha256 and tool_runtime.lock.
    return ((LOGICAL_GENERATION_ROOT / suffix).resolve(),
            LOGICAL_GENERATION_ROOT.resolve())


def main() -> int:
    oh_zlib = ROOT / "upstream/openharmony-6.1.0.31/third_party/zlib"
    target_external = (
        PLUGIN / "frozen/target_external/openharmony-6.1.0.31-d600")
    explicit = [
        PLUGIN / "SOURCE_CLOSURE.json",
        PLUGIN / "build_route_a_generation_direct.sh",
        PLUGIN / "build_route_a_generation_in_container.sh",
        PLUGIN / "build_target_in_container.sh",
        PLUGIN / "generate_generation_metadata.py",
        PLUGIN / "generate_source_closure.py",
        PLUGIN / "generate_appspawn_manager_abi_overlay.py",
        PLUGIN / "generate_route_a_inputs.py",
        PLUGIN / "verify_route_a_source.py",
        PLUGIN / "verify_stock_origin.py",
        PLUGIN / "verify_appspawn_host_abi.py",
        PLUGIN / "verify_target_artifacts.py",
        target_external / "PROVENANCE.md",
        target_external / "SHA256SUMS",
        target_external / "libbegetutil.z.so",
        target_external / "libc++.so",
        target_external / "libc.so",
        target_external / "libclang_rt.ubsan_minimal.so",
        target_external / "libconfigpolicy_util.z.so",
        target_external / "libhilog.so",
        target_external / "libsec_shared.z.so",
        target_external / "libsystemparam.z.so",
        target_external / "libutils.z.so",
        PLUGIN / "r45_adapter_identity.env",
        ROOT / "adapter/frozen/r45-dynamic-roots/README.md",
        ROOT / "adapter/frozen/r45-dynamic-roots/SHA256SUMS",
        ROOT / "adapter/frozen/r45-dynamic-roots/liboh_adapter_bridge.so",
        ROOT / "adapter/frozen/r45-dynamic-roots/liboh_android_runtime.so",
        PLUGIN / "include/westlake_android_child_plugin.h",
        PLUGIN / "include/host_runtime_services.h",
        PLUGIN / "include/runtime_loader_phase.h",
        PLUGIN / "include/sealed_child_provider_loader.h",
        PLUGIN / "include/westlake_generation_identity_facts.h",
        PLUGIN / "include/westlake_generation_identity_ops.h",
        PLUGIN / "include/westlake_generation_identity_producer.h",
        PLUGIN / "include/westlake_child_hook_table_v1.h",
        PLUGIN / "include/westlake_elf_identity.h",
        PLUGIN / "include/westlake_generation_receipt_v2.h",
        PLUGIN / "include/westlake_sha256.h",
        PLUGIN / "include/westlake_stock_host_services.h",
        PLUGIN / "patches/0001-parent-prefork-stop-on-error.patch",
        PLUGIN / "run_all.sh",
        PLUGIN / "run_host_tests.sh",
        PLUGIN / "src/stage_receipt.c",
        PLUGIN / "src/host_runtime_services.c",
        PLUGIN / "src/runtime_loader_phase.c",
        PLUGIN / "src/sealed_child_provider_loader.c",
        PLUGIN / "src/westlake_generation_identity_facts.c",
        PLUGIN / "src/westlake_generation_identity_ops.c",
        PLUGIN / "src/westlake_generation_identity_producer.c",
        PLUGIN / "src/child_hook_table_v1.c",
        PLUGIN / "src/westlake_android_child_plugin.c",
        PLUGIN / "src/westlake_android_runtime_provider.cpp",
        PLUGIN / "src/westlake_elf_identity.c",
        PLUGIN / "src/westlake_sha256.c",
        PLUGIN / "src/westlake_stock_host_main.c",
        PLUGIN / "tests/test_child_hook_table_v1.c",
        PLUGIN / "tests/include/hilog/log.h",
        PLUGIN / "tests/test_runtime_provider_child_sequence.cpp",
        PLUGIN / "tests/test_sealed_child_provider_loader.c",
        PLUGIN / "tests/test_westlake_child_hook_table_v1_layout.c",
        PLUGIN / "tests/test_westlake_generation_receipt_v2.c",
        PLUGIN / "tests/test_westlake_generation_receipt_v2.cpp",
        PLUGIN / "stock_host_patched/base/startup/appspawn/standard/appspawn_service.c",
        PLUGIN / "westlake_android_child_plugin.map",
        PLUGIN / "westlake_android_runtime_provider.map",
        PLUGIN / "westlake_stock_host.map",
        PLUGIN / "verify_route_a_generation.py",
        ROOT / "adapter/framework/appspawn-x/BUILD.gn",
        ROOT / "adapter/framework/appspawn-x/src/main.cpp",
        ROOT / "adapter/framework/appspawn-x/src/appspawnx_runtime.cpp",
        ROOT / "adapter/framework/appspawn-x/src/appspawnx_runtime.h",
        ROOT / "adapter/framework/appspawn-x/src/adapter_bridge_identity.cpp",
        ROOT / "adapter/framework/appspawn-x/src/adapter_bridge_identity.h",
        ROOT / "adapter/framework/appspawn-x/src/child_main.h",
        ROOT / "adapter/framework/appspawn-x/src/child_main_after_stock.cpp",
        ROOT / "adapter/framework/appspawn-x/src/child_main.cpp",
        ROOT / "adapter/framework/appspawn-x/src/native_compat_prepare.cpp",
        ROOT / "adapter/framework/appspawn-x/src/native_compat_prepare.h",
        ROOT / "adapter/framework/appspawn-x/src/native_compat_prepare_owner_aarch64.S",
        ROOT / "adapter/framework/appspawn-x/src/spawn_msg.h",
        ROOT / "adapter/framework/appspawn-x/tls_prefix/bionic_tls_prefix_reservation.cpp",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/include/westlake_thread_guard_registry.h",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/src/thread_guard_registry.c",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/src/thread_guard_registry_internal.h",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/src/guard_store_aarch64.S",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/westlake_thread_guard_registry.map",
        ROOT / "adapter/framework/native-compat/thread-guard-registry/tests/verify_route_a_product_integration.py",
        ROOT / "adapter/framework/native-compat/bionic-pthread-bridge/include/westlake_bionic_pthread_bridge.h",
        ROOT / "adapter/framework/native-compat/bionic-pthread-bridge/src/bionic_pthread_bridge.c",
        ROOT / "adapter/framework/native-compat/bionic-pthread-bridge/westlake_bionic_pthread_bridge.map",
        ROOT / "adapter/framework/native-compat/jni-attach-admission/include/westlake_jni_attach_admission.h",
        ROOT / "adapter/framework/native-compat/jni-attach-admission/src/jni_attach_admission.cpp",
        ROOT / "adapter/framework/native-compat/jni-attach-admission/tests/jni_attach_admission_test.cpp",
        ROOT / "adapter/framework/native-compat/jni-attach-admission/tests/run_host_tests.sh",
        ROOT / "adapter/framework/native-compat/jni-attach-admission/tests/verify_compile_closure.py",
        ROOT / "adapter/framework/native-compat/thread-template-publisher/include/westlake_thread_template_publisher.h",
        ROOT / "adapter/framework/native-compat/thread-template-publisher/src/thread_template_publisher.c",
        ROOT / "adapter/framework/native-compat/thread-template-publisher/tests/verify_product_source.py",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/system_properties.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/malloc_compat.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/fdsan_stubs.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/misc_compat.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/abort_message_compat.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/liblog_android_supplement.cpp",
        ROOT / "adapter/framework/appspawn-x/bionic_compat/src/sync_builtins.c",
        ROOT / "adapter/framework/app-native-loader/include/app_native_loader.h",
        ROOT / "adapter/framework/app-native-loader/include/oh_dlns_abi.h",
        ROOT / "adapter/framework/app-native-loader/src/app_native_loader.c",
        ROOT / "adapter/framework/app-native-loader/app_native_loader.map",
        ROOT / "adapter/framework/native-loader-oh/include/nativeloader/native_loader.h",
        ROOT / "adapter/framework/native-loader-oh/include/nativeloader/native_bridge_policy.h",
        ROOT / "adapter/framework/native-loader-oh/src/native_loader.cpp",
        ROOT / "adapter/framework/native-loader-oh/src/native_loader_registry.cpp",
        ROOT / "adapter/framework/native-loader-oh/src/native_loader_registry.h",
        ROOT / "adapter/framework/native-loader-oh/src/system_loader.cpp",
        ROOT / "adapter/framework/native-loader-oh/src/system_loader.h",
        ROOT / "adapter/framework/native-loader-oh/native_loader.map",
        ROOT / "adapter/framework/native-loader-oh/policy/native_bridge_policy.v1.json",
        ROOT / "adapter/framework/app-native-loader/tests/host/app_native_loader_host_test.c",
        ROOT / "adapter/framework/app-native-loader/tests/host/include/dlfcn.h",
        ROOT / "adapter/framework/app-native-loader/tests/host/mock_dlns.c",
        ROOT / "adapter/framework/app-native-loader/tests/host/mock_dlns.h",
        ROOT / "adapter/framework/app-native-loader/tests/host/run_host_tests.sh",
        ROOT / "adapter/build/compile_app_native_loader_arm64.sh",
        ROOT / "upstream/openharmony-6.1.0.31/base/startup/appspawn/standard/appspawn_manager.h",
        oh_zlib / "BUILD.gn",
        oh_zlib / "adler32.c",
        oh_zlib / "compress.c",
        oh_zlib / "contrib/minizip/ioapi.c",
        oh_zlib / "contrib/minizip/ioapi.h",
        oh_zlib / "contrib/minizip/unzip.c",
        oh_zlib / "contrib/minizip/unzip.h",
        oh_zlib / "contrib/minizip/zip.c",
        oh_zlib / "contrib/minizip/zip.h",
        oh_zlib / "crc32.c",
        oh_zlib / "crc32.h",
        oh_zlib / "deflate.c",
        oh_zlib / "deflate.h",
        oh_zlib / "gzclose.c",
        oh_zlib / "gzguts.h",
        oh_zlib / "gzlib.c",
        oh_zlib / "gzread.c",
        oh_zlib / "gzwrite.c",
        oh_zlib / "infback.c",
        oh_zlib / "inffast.c",
        oh_zlib / "inffast.h",
        oh_zlib / "inffixed.h",
        oh_zlib / "inflate.c",
        oh_zlib / "inflate.h",
        oh_zlib / "inftrees.c",
        oh_zlib / "inftrees.h",
        oh_zlib / "trees.c",
        oh_zlib / "trees.h",
        oh_zlib / "uncompr.c",
        oh_zlib / "zconf.h",
        oh_zlib / "zlib.h",
        oh_zlib / "zutil.c",
        oh_zlib / "zutil.h",
        generation_input("frozen.sha256"),
        generation_input("tool_runtime.lock"),
    ]
    rejected_frozen_files = {
        PLUGIN / "frozen/runtime_provider/libraries/generated/"
        "libbionic_compat.so",
        PLUGIN / "frozen/runtime_provider/libraries/aosp/libart.so",
        PLUGIN / "frozen/runtime_provider/libraries/aosp/liblog.so",
        PLUGIN / "frozen/runtime_provider/libraries/aosp/libnativehelper.so",
    }
    frozen_files = sorted(
        path for path in (PLUGIN / "frozen").rglob("*")
        if path.is_file() and path not in rejected_frozen_files
    )
    compat_headers = sorted(
        path
        for path in (ROOT / "adapter/framework/appspawn-x/bionic_compat/include").rglob("*")
        if path.is_file()
    )
    art_palette_files = sorted(
        path
        for path in (ROOT / "adapter/framework/art-palette-oh").rglob("*")
        if path.is_file()
    )
    app_loader_test_files = sorted(
        path
        for path in (ROOT / "adapter/framework/app-native-loader/tests").rglob("*")
        if path.is_file()
    )
    provenance = PLUGIN / "frozen/PROVENANCE.tsv"
    provenance_lines = provenance.read_text().splitlines()
    if not provenance_lines or provenance_lines[0] != (
        "destination\tsha256\tproject_local_origin"
    ):
        raise SystemExit("invalid frozen provenance header")
    recorded_destinations: set[Path] = set()
    unavailable_origins: list[str] = []
    for line in provenance_lines[1:]:
        destination_text, expected_sha, origin_text = line.split("\t")
        destination = (PLUGIN / "frozen" / destination_text).resolve()
        if destination in {path.resolve() for path in rejected_frozen_files}:
            continue
        origin, origin_root = provenance_origin(origin_text)
        destination.relative_to((PLUGIN / "frozen").resolve())
        origin.relative_to(origin_root)
        if not destination.is_file():
            raise SystemExit(f"missing frozen provenance edge: {line}")
        if digest(destination) != expected_sha:
            raise SystemExit(f"frozen provenance hash mismatch: {line}")
        if not origin.is_file():
            unavailable_origins.append(origin_text)
        elif digest(origin) != expected_sha:
            raise SystemExit(f"frozen provenance origin mismatch: {line}")
        recorded_destinations.add(destination)
    library_files = {
        path.resolve() for path in (PLUGIN / "frozen").rglob("*.so")
        if path.is_file() and path not in rejected_frozen_files
    }
    if library_files != recorded_destinations:
        raise SystemExit("frozen library provenance set mismatch")
    oh_root = ROOT / "adapter/frozen/references/oh-appspawn-security-v7"
    auxiliary_roots = [
        oh_root / "base/startup/init",
        oh_root / "interface/sdk_c/hiviewdfx/hilog",
        oh_root / "third_party/bounds_checking_function/include",
        oh_root / "third_party/cJSON",
        oh_root / "aux",
    ]
    auxiliary_files = sorted(
        path
        for directory in auxiliary_roots
        for path in directory.rglob("*")
        if path.is_file()
    )
    canonical_oh = ROOT / "upstream/openharmony-6.1.0.31"
    systemparam_roots = [
        canonical_oh / "base/startup/init/interfaces/innerkits",
        canonical_oh / "base/startup/init/interfaces/hals",
        canonical_oh / "base/startup/init/services/param/include",
        canonical_oh / "base/startup/init/services/log",
        canonical_oh / "base/startup/init/services/utils",
        canonical_oh / "base/startup/init/services/modules/udid",
        canonical_oh / "base/hiviewdfx/hilog/interfaces/native/innerkits/include",
        canonical_oh / "third_party/bounds_checking_function/include",
    ]
    systemparam_source_files = sorted(
        path
        for directory in systemparam_roots
        for path in directory.rglob("*")
        if path.is_file()
    )
    files = sorted(
        set(explicit + frozen_files + compat_headers + art_palette_files +
            app_loader_test_files + auxiliary_files + systemparam_source_files),
        key=relative,
    )
    missing = [relative(path) for path in files if not path.is_file()]
    if missing:
        raise SystemExit(f"missing Route A input(s): {missing}")
    entries = [
        {
            "path": relative(path),
            "sha256": digest(path),
            "size": path.stat().st_size,
        }
        for path in files
    ]
    source_closure = json.loads((PLUGIN / "SOURCE_CLOSURE.json").read_text())
    document = {
        "schema": "westlake.route-a-input-closure.v1",
        "source_closure_tree_sha256": source_closure["tree_sha256"],
        "security_operation_owner": "stock_OH_appspawn_only",
        "provider_security_operations_mask": 0,
        "stock_normal_spawn": True,
        "oh_prefork_feature_stubbed": True,
        "unused_trace_and_dfx_dump_stubbed": True,
        "frozen_library_provenance_verified": True,
        "frozen_library_origins_available": not unavailable_origins,
        "unavailable_frozen_library_origins": sorted(unavailable_origins),
        "files": entries,
    }
    output = PLUGIN / "ROUTE_A_INPUTS.json"
    payload = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if "--verify" in __import__("sys").argv:
        if not output.is_file() or output.read_text() != payload:
            raise SystemExit("Route A input ledger drift")
        print(f"PASS Route A input closure files={len(entries)} sha256={digest(output)}")
        return 0
    output.write_text(payload)
    print(f"wrote {output} files={len(entries)} sha256={digest(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
