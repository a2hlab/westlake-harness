#!/usr/bin/env python3
"""Regression gate for Fn01.A02 authoritative package queries.

This target has no host-side fake BMS: its contract is deliberately narrow.
When the real BMS is disconnected or has no record, the JNI boundary must
return an empty result.  In particular, a bring-up APK name must never unlock
a synthetic BundleInfo record.
"""

from pathlib import Path
import re
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1] / "jni" / "oh_bundle_mgr_client.cpp"
).read_text(encoding="utf-8")


class BundleQueryFailClosedContractTest(unittest.TestCase):
    def test_no_known_apk_or_synthetic_bundle_fallback_is_embedded(self):
        self.assertNotIn("SynthesizeSelfBundleInfoJson", SOURCE)
        self.assertNotIn('"com.example.helloworld"', SOURCE)
        self.assertNotIn('"com.example.HelloWorld"', SOURCE)
        self.assertNotIn("DAYU200", SOURCE)
        self.assertNotIn("return userId > 0 ? userId : 100", SOURCE)

    def test_disconnected_and_missing_bms_paths_return_empty(self):
        get_bundle_info = re.search(
            r"std::string OHBundleMgrClient::getBundleInfo.*?\n}\n",
            SOURCE,
            re.DOTALL,
        )
        self.assertIsNotNone(get_bundle_info)
        body = get_bundle_info.group(0)
        self.assertRegex(
            body,
            r"(?s)if \(!connect\(\)\) \{.*?return \"\";.*?\}",
        )
        self.assertRegex(
            body,
            r"(?s)if \(!result\) \{.*?return \"\";.*?\}",
        )


if __name__ == "__main__":
    unittest.main()
