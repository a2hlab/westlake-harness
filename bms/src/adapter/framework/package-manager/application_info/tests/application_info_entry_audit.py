#!/usr/bin/env python3
"""Static production-entry audit for Fn01.A05; never issues a verdict."""

from pathlib import Path
import re
import sys


root = Path(__file__).resolve().parents[2]
adapter = (root / "java" / "PackageManagerAdapter.java").read_text()
builder = (root / "java" / "PackageInfoBuilder.java").read_text()
jni = (root / "jni" / "application_info_jni.cpp").read_text()
owner = (
    root / "application_info" / "src"
    / "application_info_runtime_owner_v1.cpp"
).read_text()
canonical_lifecycle = (
    root.parents[0] / "core" / "jni" / "oh_environment.cpp"
).read_text()
snapshot_lifecycle = (
    root.parents[1] / "sources" / "oh61-v7-b2133b5b"
    / "framework" / "core" / "jni" / "oh_environment.cpp"
).read_text()
launcher_configs = [
    root.parents[1] / "config" / "appspawn_x.cfg",
    root.parents[0] / "appspawn-x" / "config" / "appspawn_x.cfg",
    root.parents[0] / "appspawn-x" / "src" / "appspawn_x.cfg",
    root.parents[1] / "sources" / "oh61-v7-b2133b5b"
    / "framework" / "appspawn-x" / "config" / "appspawn_x.cfg",
    root.parents[1] / "sources" / "oh61-v7-b2133b5b"
    / "framework" / "appspawn-x" / "src" / "appspawn_x.cfg",
]
standalone_build = (
    root.parents[1]
    / "sources"
    / "oh61-v7-b2133b5b"
    / "build"
    / "inner"
    / "compile_oh_adapter_bridge_arm64.sh"
).read_text()


def _method_body(source: str, name: str) -> str:
    start = source.find(name)
    if start < 0:
        return ""
    end = source.find("\n    private static", start)
    return source[start:end if end >= 0 else len(source)]


match = re.search(
    r"public ApplicationInfo getApplicationInfo"
    r"\(String packageName, long flags, int userId\)",
    adapter,
)
if match is None:
    raise SystemExit("FAIL: Android getApplicationInfo override not found")
next_method = adapter.find("\n    /**", match.end())
body = adapter[match.end():next_method if next_method >= 0 else len(adapter)]
typed_query_body = _method_body(adapter, "queryCanonicalApplicationInfo(")
checks = {
    "android_entry_calls_canonical_native":
        "queryCanonicalApplicationInfo" in body
        and "nativeGetCanonicalApplicationInfo" in typed_query_body,
    "android_entry_passes_binder_caller":
        "Binder.getCallingUid()" in typed_query_body,
    "android_entry_avoids_bundleinfo":
        "nativeGetApplicationInfo(" not in body
        and "fromBundleInfo" not in body,
    "android_entry_builds_canonical_dto":
        "decodeCanonicalApplicationInfo" in typed_query_body,
    "jni_export_present":
        "PackageManagerAdapter_nativeGetCanonicalApplicationInfo" in jni,
    "jni_routes_runtime_core":
        "QueryCanonicalApplicationInfoEntryV1" in jni,
    "target_build_uses_canonical_pm_root":
        'PM_SOURCE_ROOT="${PACKAGE_MANAGER_SOURCE_ROOT:-'
        '$ADAPTER_ROOT/../../framework/package-manager}"'
        in standalone_build,
    "target_build_includes_jni":
        '"$PM_SOURCE_ROOT/jni/application_info_jni.cpp"'
        in standalone_build,
    "target_build_includes_core":
        '"$PM_SOURCE_ROOT/application_info/src/application_info_v1.cpp"'
        in standalone_build,
    "target_build_includes_runtime":
        '"$PM_SOURCE_ROOT/application_info/src/'
        'application_info_runtime_v1.cpp"' in standalone_build,
    "target_build_includes_public_entry":
        '"$PM_SOURCE_ROOT/application_info/src/'
        'application_info_public_entry_v1.cpp"' in standalone_build,
    "target_build_includes_runtime_owner":
        '"$PM_SOURCE_ROOT/application_info/src/'
        'application_info_runtime_owner_v1.cpp"' in standalone_build,
    "product_owner_configures_runtime":
        "ConfigureApplicationInfoRuntimeV1" in owner
        and "ClearApplicationInfoRuntimeV1" in owner,
    "product_owner_has_no_absolute_state_root":
        "/data/" not in owner and "OH_ADAPTER_FN01_STATE_ROOT" in owner,
    "product_launcher_injects_state_root":
        all(
            "OH_ADAPTER_FN01_STATE_ROOT" in path.read_text()
            for path in launcher_configs
        ),
    "public_runtime_preserves_typed_caller_failures":
        "ApplicationInfoCallerVerdictV1::PACKAGE_NOT_FOUND" in (
            root / "application_info" / "src"
            / "application_info_runtime_v1.cpp"
        ).read_text()
        and "ApplicationInfoCallerVerdictV1::PACKAGE_NOT_READY" in (
            root / "application_info" / "src"
            / "application_info_runtime_v1.cpp"
        ).read_text(),
    "public_entry_retries_deferred_owner":
        "StartProductApplicationInfoRuntimeV1" in (
            root / "application_info" / "src"
            / "application_info_public_entry_v1.cpp"
        ).read_text(),
    "java_exposes_typed_query_envelope":
        "CanonicalApplicationInfoResult" in builder
        and "decodeCanonicalApplicationInfo" in builder
        and "queryCanonicalApplicationInfo" in adapter,
    "android_entry_logs_typed_failure":
        "result.verdict" in body and "result.reason" in body,
    "canonical_lifecycle_starts_and_stops_owner":
        "StartProductApplicationInfoRuntimeV1" in canonical_lifecycle
        and "StopProductApplicationInfoRuntimeV1" in canonical_lifecycle,
    "snapshot_lifecycle_starts_and_stops_owner":
        "StartProductApplicationInfoRuntimeV1" in snapshot_lifecycle
        and "StopProductApplicationInfoRuntimeV1" in snapshot_lifecycle,
    "builder_preserves_non_ready_verdict":
        'if (!"READY".equals(verdict))' in builder
        and "new CanonicalApplicationInfoResult(" in builder,
    "builder_requires_paths":
        'view.getString("sourceDir")' in builder
        and 'view.getString("dataDir")' in builder,
    "builder_avoids_guess_paths":
        '"/system/app/" + packageName' not in
        _method_body(builder, "fromCanonicalApplicationInfo"),
}

for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
if not all(checks.values()):
    sys.exit(1)
print("PASS fn01_a05_android_compatibility_entry static_only=true")
