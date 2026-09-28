#!/usr/bin/env python3
"""Static contract for the Bridge raw-APK special install path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ENTRY = (ROOT / "jni" / "oh_adapter_install_apk_c_entry.cpp").read_text(
    encoding="utf-8"
)
BMS_PATCH = (
    ROOT.parents[1]
    / "ohos_patches/foundation/bundlemanager/bundle_framework/services/"
    / "bundlemgr/src/base_bundle_installer.cpp.patch"
).read_text(encoding="utf-8")


class ApkSpecialPathContractTest(unittest.TestCase):
    def test_manifest_bridge_labels_special_path_not_general_installer(self):
        self.assertIn('"bridge_raw_apk_special_v1"', ENTRY)
        self.assertIn('json["generalAndroidApkInstall"] = false;', ENTRY)
        self.assertIn('json["requiresBridgeVerifier"] = true;', ENTRY)
        self.assertIn('"requires_bionic_runtime_bridge"', ENTRY)

    def test_bms_rejects_missing_or_generalized_profile(self):
        self.assertIn('"installCompatibilityProfile"', BMS_PATCH)
        self.assertIn('"generalAndroidApkInstall"', BMS_PATCH)
        self.assertIn('"requiresBridgeVerifier"', BMS_PATCH)
        self.assertIn('installCompatibilityProfile != "bridge_raw_apk_special_v1"', BMS_PATCH)
        self.assertIn("generalAndroidApkInstall || !requiresBridgeVerifier", BMS_PATCH)

    def test_native_payload_marks_bionic_runtime_dependency(self):
        self.assertIn('"nativeRuntimeCompatibility"', BMS_PATCH)
        self.assertIn('"requires_bionic_runtime_bridge"', BMS_PATCH)
        self.assertIn('"not_applicable"', BMS_PATCH)


if __name__ == "__main__":
    unittest.main()
