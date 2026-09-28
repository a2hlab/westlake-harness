#!/usr/bin/env python3
"""Static production-entry audit for Fn01.A04; does not issue a verdict."""

from pathlib import Path
import re
import sys


root = Path(__file__).resolve().parents[2]
adapter = (root / "java" / "PackageManagerAdapter.java").read_text()
builder = (root / "java" / "PackageInfoBuilder.java").read_text()
jni = (root / "jni" / "package_info_jni.cpp").read_text()
bridge_build = (root.parent / "jni" / "BUILD.gn").read_text()
standalone_build = (
    root.parents[1]
    / "sources"
    / "oh61-v7-b2133b5b"
    / "build"
    / "inner"
    / "compile_oh_adapter_bridge_arm64.sh"
).read_text()

match = re.search(
    r"public PackageInfo getPackageInfo\(String packageName, long flags, int userId\)",
    adapter,
)
if match is None:
    raise SystemExit("FAIL: Android getPackageInfo override not found")
next_method = adapter.find("\n    /**", match.end())
body = adapter[match.end():next_method if next_method >= 0 else len(adapter)]
checks = {
    "android_entry_calls_canonical_native":
        "nativeGetCanonicalPackageInfo" in body,
    "android_entry_passes_binder_caller":
        "Binder.getCallingUid()" in body,
    "android_entry_avoids_bundleinfo":
        "nativeGetBundleInfo" not in body and "fromBundleInfo" not in body,
    "android_entry_builds_canonical_dto":
        "fromCanonicalPackageInfo" in body,
    "jni_export_present":
        "PackageManagerAdapter_nativeGetCanonicalPackageInfo" in jni,
    "jni_routes_runtime_core":
        "QueryPackageInfoRuntimeJsonV1" in jni,
    "bridge_build_includes_jni":
        "../package-manager/jni/package_info_jni.cpp" in bridge_build,
    "target_build_uses_canonical_pm_root":
        'PM_SOURCE_ROOT="${PACKAGE_MANAGER_SOURCE_ROOT:-$ADAPTER_ROOT/../../framework/package-manager}"'
        in standalone_build,
    "target_build_includes_jni":
        '"$PM_SOURCE_ROOT/jni/package_info_jni.cpp"' in standalone_build,
    "target_build_includes_transaction":
        '"$PM_SOURCE_ROOT/package_transaction/src/package_transaction_v1.cpp"'
        in standalone_build,
    "target_build_includes_package_info_core":
        '"$PM_SOURCE_ROOT/package_info/src/package_info_v1.cpp"'
        in standalone_build,
    "target_build_includes_package_info_runtime":
        '"$PM_SOURCE_ROOT/package_info/src/package_info_runtime_v1.cpp"'
        in standalone_build,
    "builder_rejects_non_ready":
        '"READY".equals(response.optString("verdict"))' in builder,
    "builder_uses_real_signature_bytes":
        'new Signature(certificates.getString(i))' in builder,
    "builder_constructs_signing_info":
        "new SigningInfo(details)" in builder,
}
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
if not all(checks.values()):
    sys.exit(1)
print("PASS fn01_a04_android_compatibility_entry static_only=true")
