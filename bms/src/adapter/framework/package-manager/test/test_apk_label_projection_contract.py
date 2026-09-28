#!/usr/bin/env python3
"""Static contract for resource-backed APK labels at the BMS JSON boundary."""

from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
ENTRY = (PACKAGE_DIR / "jni/oh_adapter_install_apk_c_entry.cpp").read_text()
LABEL_HEADER = (PACKAGE_DIR / "jni/apk_label_resolver.h").read_text()
LABEL_SOURCE = (PACKAGE_DIR / "jni/apk_label_resolver.cpp").read_text()
ARSC_HEADER = (PACKAGE_DIR / "jni/arsc_resolver.h").read_text()
ARSC_SOURCE = (PACKAGE_DIR / "jni/arsc_resolver.cpp").read_text()
BUILD = (PACKAGE_DIR / "BUILD.gn").read_text()


def require(fragment: str, text: str, source: str) -> None:
    if fragment not in text:
        raise AssertionError(f"missing {fragment!r} in {source}")


require("ResolveApkResourceIdToString", ARSC_HEADER, "arsc_resolver.h")
require("packageId == 0x01", ARSC_SOURCE, "arsc_resolver.cpp")
require("/system/android/framework/framework-res.apk", ARSC_SOURCE, "arsc_resolver.cpp")
require('"jni/arsc_resolver.cpp"', BUILD, "BUILD.gn")
if BUILD.count('"jni/arsc_resolver.cpp"') != 1:
    raise AssertionError("arsc_resolver.cpp must be linked into apk_installer exactly once")

require("ResolveApkLabel", LABEL_HEADER, "apk_label_resolver.h")
require("ResolveApkResourceIdToString", LABEL_SOURCE, "apk_label_resolver.cpp")
require('"jni/apk_label_resolver.cpp"', BUILD, "BUILD.gn")
require('#include "apk_label_resolver.h"', ENTRY, "oh_adapter_install_apk_c_entry.cpp")
require("manifest.appLabelResId", ENTRY, "oh_adapter_install_apk_c_entry.cpp")
require("activity.labelResId", ENTRY, "oh_adapter_install_apk_c_entry.cpp")
require('json["appLabel"] = appLabel;', ENTRY, "oh_adapter_install_apk_c_entry.cpp")
require("activity.label, activity.labelResId, appLabel", ENTRY,
        "oh_adapter_install_apk_c_entry.cpp")

# These two expressions were the first-bad: resource references have empty
# literal strings, so both forms discard the retained resource IDs.
for forbidden in (
    "manifest.appLabel.empty() ? manifest.packageName : manifest.appLabel",
    "activity.label.empty() ? manifest.appLabel : activity.label",
):
    if forbidden in ENTRY:
        raise AssertionError(f"resource-backed label regression remains: {forbidden}")

print("APK_LABEL_PROJECTION_CONTRACT=PASS")
