#!/usr/bin/env python3
"""Static guard for the fail-fast multi-package lifecycle boundary.

BMS owns exactly one APK transaction. The outer harness owns sequencing and
must stop after the first failed member. This is not a device verdict.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/base_bundle_installer.cpp.patch"
STREAM = ROOT / "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_stream_installer_host_impl.cpp.patch"
RESTORE = ROOT.parent / "restore_after_sync.sh"
ENTRY = ROOT.parent / "framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp"
HARNESS = ROOT.parents[2] / "src/tools/experiments/d600/run_apk_lifecycle.py"
EXACT_ONE_UPGRADE = ROOT / "foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_stream_installer_exact_one_upgrade.cpp.patch"


def require(text: str, needle: str, source: Path) -> None:
    if needle not in text:
        raise SystemExit(f"missing contract {needle!r} in {source}")


base = BASE.read_text(encoding="utf-8")
stream = STREAM.read_text(encoding="utf-8")
restore = RESTORE.read_text(encoding="utf-8")
entry = ENTRY.read_text(encoding="utf-8")
harness = HARNESS.read_text(encoding="utf-8")
exact_one_upgrade = EXACT_ONE_UPGRADE.read_text(encoding="utf-8")

require(base, "if (apkCount != 1 || bundlePaths.size() != 1)", BASE)
require(base, "One Android package is one BMS transaction", BASE)
require(stream, "if (apkCount != 1 || appPaths.size() != 1)", STREAM)
require(stream, "single APK retained for BaseBundleInstaller route", STREAM)
if "APK list retained for per-APK BaseBundleInstaller route" in stream:
    raise SystemExit("stream installer still overloads the BMS vector route")

if '"foundation/bundlemanager/bundle_framework/services/bundlemgr/src/bundle_installer.cpp.patch"' in restore:
    raise SystemExit("restore activates the disabled competing installer ABI")
require(restore, "bundle_stream_installer_exact_one_upgrade.cpp.patch", RESTORE)
if "bundle_stream_installer_multi_apk_upgrade.cpp.patch" in restore:
    raise SystemExit("restore still contains the cross-package vector upgrade")
require(exact_one_upgrade, "appPaths.size() > 1", EXACT_ONE_UPGRADE)

verify_pos = entry.index(
    "ApkVerifierClient::OpenAndVerify(",
    entry.index("oh_adapter_install_apk_with_manifest"),
)
parse_pos = entry.index("ApkManifestParser::Parse(immutablePath, manifest)", verify_pos)
if verify_pos >= parse_pos:
    raise SystemExit("manifest projection is not derived from the verified fd")

require(harness, "def run_fail_fast_queue(", HARNESS)
require(harness, '"queue_policy"] = "fail_fast_single_package_transactions"', HARNESS)
require(harness, "return outcomes, stopped_at, [member.package for member in apps[index:]]", HARNESS)

print("multi-package fail-fast route contract PASS")
