import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def require_identity(data, expected):
    if data["sha256"] != expected:
        raise ValueError("Deployed identity mismatch; same filename is not sufficient")


class EvidenceTests(unittest.TestCase):
    def test_exact_runtime_and_boot_not_stale(self):
        runtime = read("evidence/runtime-dex.json")
        boot = read("evidence/boot-dex.json")
        require_identity(runtime, "5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108")
        require_identity(boot, "3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af")
        stale = copy.deepcopy(runtime)
        stale["sha256"] = "d5000c4e" + "0" * 56
        with self.assertRaises(ValueError):
            require_identity(stale, runtime["sha256"])

    def test_both_seeders_and_per_view_cache(self):
        runtime = read("evidence/runtime-dex.json")["lines"]
        boot = read("evidence/boot-dex.json")["lines"]
        methods = {(row["owner"], row["method"]) for row in runtime}
        for owner in ["WebViewProviderFix", "J10eWebView", "J10gWebExtras"]:
            self.assertIn(("Ladapter/activity/" + owner + ";", "install"), methods)
        for text in ["sProviderInstance", "mProvider"]:
            self.assertTrue(any(text in row["text"] for row in boot))
        self.assertEqual(len(read("cache-changes.json")["changes"]), 7)

    def test_aosp14_for_t_and_service_process_selection(self):
        boot = read("evidence/boot-dex.json")["lines"]
        self.assertTrue(any("WebViewChromiumFactoryProviderForT" in row["text"] for row in boot))
        calls = [row["text"] for row in boot if row["owner"] == "Landroid/webkit/WebViewDelegate;"
                 and row["method"] == "isMultiProcessEnabled"]
        self.assertTrue(any("IWebViewUpdateService;.isMultiProcessEnabled" in text for text in calls))
        self.assertFalse(any("Flags;" in text for text in calls))
        provider = read("evidence/provider-dex.json")["lines"]
        self.assertTrue(any(row["method"] == "create" and "ForT;" in row["owner"] for row in provider))

    def test_inventory_is_not_namespace_or_historical_pass(self):
        donor = read("donors.json")
        closure = read("evidence/closure.json")
        self.assertEqual(len(closure["needed"]), 6)
        self.assertEqual(donor["strong_undefined_count"], 423)
        self.assertEqual(len(donor["missing_from_inventory"]), 13)
        self.assertIn("wl_ismember", donor["missing_from_inventory"])
        self.assertFalse(donor["extracted_chromium_matches_apk_member"])
        self.assertFalse(donor["verified_historical_method"]["raw_results_available_locally"])
        self.assertEqual(donor["provider_namespace_visibility"], "unproved")

    def test_shipped_evidence_hashes_and_no_private_requirements(self):
        for item in read("evidence-index.json"):
            path = HERE / item["path"]
            self.assertTrue(path.is_file())
            self.assertNotIn(".artifacts", item["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), item["sha256"])
        self.assertEqual(len(read("evidence/six-keys.json")["rows"]), 6)


class PhaseTests(unittest.TestCase):
    def test_presence_and_fatals_move_zero(self):
        data = read("results.json")
        self.assertEqual(data["phases"][0]["content_moves"], 0)
        self.assertEqual(data["proven_first_fatal_moves"], 0)
        self.assertEqual(data["proven_content_moves"], 0)
        self.assertEqual(data["html_compat_restore_content_moves"], 0)
        for row in data["rows"]:
            self.assertEqual(row["first_fatal_moves"], 0)

    def test_local_four_remote_one_control_not_gain(self):
        data = read("results.json")
        local = {row["key"] for row in data["rows"] if row["phase1_conditional_content_move"]}
        remote = {row["key"] for row in data["rows"] if row["phase2_additional_conditional_content_move"]}
        self.assertEqual(len(local), 4)
        self.assertEqual(remote, {"cv2-dev-obfusk-jiten-webview"})
        self.assertFalse(local & remote)
        self.assertEqual(len(local | remote), 5)
        control = next(row for row in data["rows"] if row["already_lit_control"])
        self.assertEqual(control["key"], "cv2-com-caniwebview-android")
        self.assertEqual(data["guaranteed_new_lit_keys"], 0)

    def test_local_rtc_content_does_not_need_camera(self):
        keys = read("evidence/six-keys.json")["rows"]
        rtc = next(row for row in keys if row["key"] == "cv2-timur-webrtc-check")
        index = next(item for item in rtc["html"] if item["member"] == "assets/index.html")
        self.assertIn("WebRTC-Check", index["text"])
        self.assertIn("Android.webviewVersion()", index["text"])
        self.assertNotIn("getUserMedia", index["text"])
        capacitors = [row for row in keys if row["config"]]
        self.assertEqual(len(capacitors), 3)
        self.assertTrue(all("assets/public/index.html" in row["assets"] for row in capacitors))

    def test_read_only_and_conditional_effort(self):
        data = read("results.json")
        self.assertFalse(data["execution_enabled"])
        self.assertEqual(data["candidates_created"] + data["board_operations"] + data["builds"], 0)
        self.assertEqual(data["effort"]["unit"], "agent round")
        for stage in data["phases"]:
            self.assertGreater(stage["rounds_including_integration_and_verification"][1],
                               stage["rounds_including_integration_and_verification"][0])
        self.assertIn("Main-thread JS", data["phases"][1]["acceptance"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["evidence", "phases"])
    args = parser.parse_args()
    suite = unittest.TestSuite()
    for name, tests in [("evidence", EvidenceTests), ("phases", PhaseTests)]:
        if args.part in (None, name):
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(tests))
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
