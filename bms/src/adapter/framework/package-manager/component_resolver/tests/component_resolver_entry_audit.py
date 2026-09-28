#!/usr/bin/env python3
"""Static production-entry audit for Fn01.A06; never issues a verdict."""

from pathlib import Path
import re
import sys


pm_root = Path(__file__).resolve().parents[2]
adapter_root = pm_root.parents[1]
adapter = (pm_root / "java" / "PackageManagerAdapter.java").read_text()
jni = (pm_root / "jni" / "component_resolver_jni.cpp").read_text()
runtime = (
    pm_root
    / "component_resolver"
    / "src"
    / "component_resolver_runtime_v1.cpp"
).read_text()
environment = (
    adapter_root / "framework" / "core" / "jni" / "oh_environment.cpp"
).read_text()
standalone_build = (
    adapter_root
    / "sources"
    / "oh61-v7-b2133b5b"
    / "build"
    / "inner"
    / "compile_oh_adapter_bridge_arm64.sh"
).read_text()


def method_body(name: str) -> str:
    match = re.search(r"public [^{;]+ " + re.escape(name) + r"\([^)]*\)", adapter)
    if match is None:
        return ""
    next_override = adapter.find("\n    @Override", match.end())
    return adapter[match.start():next_override if next_override >= 0 else len(adapter)]


activity_body = method_body("queryIntentActivities")
checks = {
    "android_activity_entry_uses_canonical":
        "queryCanonicalComponents" in activity_body,
    "android_activity_entry_avoids_oh_resolver":
        "nativeQueryAbilityInfos" not in activity_body
        and "intentToWant" not in activity_body,
    "android_service_entry_uses_canonical":
        "queryCanonicalComponents" in method_body("queryIntentServices"),
    "android_receiver_entry_uses_canonical":
        "queryCanonicalComponents" in method_body("queryIntentReceivers"),
    "android_provider_entry_uses_canonical":
        "queryCanonicalComponents" in method_body("queryIntentContentProviders"),
    "binder_caller_reaches_native":
        "Binder.getCallingUid()" in adapter
        and "nativeResolveCanonicalComponents" in adapter,
    "typed_receipt_publicly_observable":
        "public static String getLastComponentResolveReceiptJson()" in adapter
        and "sLastComponentResolveReceipt.set" in adapter,
    "request_id_restart_unique":
        "java.util.UUID.randomUUID()" in adapter,
    "snapshot_anchor_reaches_jni":
        "setComponentResolveSnapshotAnchor(" in adapter
        and "expectedCatalogRevision" in adapter
        and "expectedCatalogRevision" in jni
        and "request.expectedCatalogRevision" in jni
        and "request.expectedCanonicalDigest" in jni,
    "jni_export_present":
        "PackageManagerAdapter_nativeResolveCanonicalComponents" in jni,
    "jni_routes_runtime_core":
        "QueryComponentResolverRuntimeJsonV1" in jni,
    "runtime_has_no_permissive_default":
        "COMPONENT_RESOLVER_RUNTIME_NOT_CONFIGURED" in runtime,
    "runtime_uses_package_store":
        "FilePackageStore" in runtime and "ReadPackageManagementState" in runtime,
    "caller_scope_private_and_mode_checked":
        "/data/service/el1/private/appspawnx/fn01/caller-scope-v1" in runtime
        and "caller scope owner or mode is not trusted" in runtime,
    "startup_owner_started":
        "StartProductComponentResolverRuntimeV1" in environment,
    "startup_owner_stopped":
        "StopProductComponentResolverRuntimeV1" in environment,
    "target_build_includes_jni":
        '"$PM_SOURCE_ROOT/jni/component_resolver_jni.cpp"' in standalone_build,
    "target_build_includes_core":
        '"$PM_SOURCE_ROOT/component_resolver/src/component_resolver_v1.cpp"'
        in standalone_build,
    "target_build_includes_runtime":
        '"$PM_SOURCE_ROOT/component_resolver/src/'
        'component_resolver_runtime_v1.cpp"' in standalone_build,
}

for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'} {name}")
if not all(checks.values()):
    sys.exit(1)
print("PASS fn01_a06_android_compatibility_entry static_only=true")
