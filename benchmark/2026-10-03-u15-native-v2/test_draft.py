import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from validation import ANL, CHANGES, check_partial, check_review, check_routes

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class CompositionTests(unittest.TestCase):
    def test_five_paths_and_disabled_scope(self):
        check_partial(load("manifests/old-native-manifest.json")["files"], load("manifests/native-manifest.json")["files"], load("composition.json"))

    def test_split_alias_rejected(self):
        new = load("manifests/native-manifest.json")["files"]
        new["payload/route/libapp_native_loader.so"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "both ANL aliases"):
            check_partial(load("manifests/old-native-manifest.json")["files"], new, load("composition.json"))

    def test_extra_payload_rejected(self):
        new = load("manifests/native-manifest.json")["files"]
        new["payload/android/lib64/new.so"] = ANL
        with self.assertRaises(ValueError):
            check_partial(load("manifests/old-native-manifest.json")["files"], new, load("composition.json"))

    def test_descriptor_or_historical_pair_rejected(self):
        old = load("manifests/old-native-manifest.json")["files"]
        new = load("manifests/native-manifest.json")["files"]
        state = load("composition.json")
        with self.assertRaisesRegex(ValueError, "execution or promotion"):
            check_partial(old, new, state, True)
        state["paired_receipt"] = "old U14 receipt"
        with self.assertRaisesRegex(ValueError, "Historical images"):
            check_partial(old, new, state)

    def test_package_lists_and_runtime_publication(self):
        packages = check_routes((HERE / "inputs/source/u15-app-native-loader.c").read_text(), (HERE / "inputs/source/n4-host.c").read_text())
        self.assertEqual(packages, load("route-lists.json")["anl_packages"])
        self.assertEqual(len(packages), 14)

    def test_one_list_or_runtime_only_rejected(self):
        anl = (HERE / "inputs/source/u15-app-native-loader.c").read_text()
        host = (HERE / "inputs/source/n4-host.c").read_text()
        with self.assertRaisesRegex(ValueError, "lists must match"):
            check_routes(anl.replace(', "org.jitsi.meet"', ""), host)
        with self.assertRaisesRegex(ValueError, "publication"):
            check_routes(anl, host.replace('"/org.jitsi.meet/"', '"/not-jitsi/"'))

    def test_sources_and_manifest_bindings(self):
        for row in load("source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        state = load("composition.json")
        scan = load("manifests/scan-manifest.json")
        files = load("manifests/native-manifest.json")["files"]
        for profile in scan["profiles"]:
            self.assertEqual(profile["identity"]["manifest_sha256"], state["native_manifest_sha256"])
            self.assertEqual(profile["identity"]["artifact_sha256"], files[profile["identity"]["artifact"]])
        self.assertEqual(load("manifests/native-inputs.json")["namespaces"]["owner_artifact"]["sha256"], ANL)


class ReviewTests(unittest.TestCase):
    def test_raw_reports_and_unsigned_preview(self):
        report = load("report-summary.json")
        check_review(report)
        self.assertEqual(report["identical_preview_count"], 204)
        self.assertEqual(report["new_findings_by_gate"], {"N1": 0, "N2": 0})
        self.assertEqual(report["native_errors"], [])
        self.assertFalse(load("registry-delta.json")["applied"])
        self.assertIsNone(load("needs-outer-review.json")["approved_by"])

    def test_missing_raw_status_or_false_approval_rejected(self):
        for field, value in [("approvals_applied", True), ("production_run", True)]:
            report = load("report-summary.json")
            report[field] = value
            with self.assertRaises(ValueError):
                check_review(report)
        report = load("report-summary.json")
        report["records"][0].pop("exit_code")
        with self.assertRaisesRegex(ValueError, "raw return codes"):
            check_review(report)

    def test_abi_scope_and_calls_are_reported_separately(self):
        report = load("report-summary.json")
        self.assertEqual(report["consumer_count"], 219)
        for name, row in report["abi"].items():
            for key in ["removed", "drift", "consumer_breaks"]:
                self.assertEqual(row[key], 0)
            self.assertEqual(row["added"], 3 if name == "flutter" else 0)
        self.assertEqual(report["abi"]["runtime"]["call_diffs"], 1)
        self.assertEqual(report["abi"]["host"]["call_diffs"], 0)
        self.assertEqual(report["abi"]["anl"]["call_diffs"], 0)

    def test_open_namespace_delta_schema_is_complete(self):
        for row in load("static-deltas.json")["members"]:
            delta = row["open_site_delta"]
            self.assertEqual(set(delta), {"added", "removed", "namespace_api_changes", "namespace_literal_changes"})
            self.assertEqual(delta["added"], [])
            self.assertEqual(delta["removed"], [])
            self.assertEqual(delta["namespace_api_changes"], {})
            self.assertTrue(row["needed_unchanged"])
            self.assertIsNone(row["approved_by"])

    def test_flutter_direct_runtime_binding_and_unsigned_strings(self):
        abi = load("evidence/abi-flutter.json")
        self.assertEqual(abi["added"], ["ATrace_beginSection", "ATrace_endSection", "ATrace_isEnabled"])
        dynsym = (HERE / "evidence/dynsym-flutter-u15.txt").read_text()
        runtime = (HERE / "evidence/dynsym-runtime-u15.txt").read_text()
        for name in ["atrace_get_enabled_tags", "atrace_begin_body", "atrace_end_body"]:
            self.assertIn("UND " + name, dynsym)
            self.assertTrue(any(name in line and " UND " not in line for line in runtime.splitlines()))
        self.assertIn("liboh_android_runtime.so", (HERE / "evidence/dynamic-flutter-u15.txt").read_text())
        review = load("strings-review.json")
        self.assertFalse(review["applied"])
        self.assertIsNone(review["approved_by"])
        self.assertEqual(set(review["objects"]), {"runtime", "host", "anl", "flutter"})
        self.assertEqual(len(review["rows"]), 20)
        self.assertEqual(review["objects"]["flutter"]["added"], 0)
        for row in review["rows"]:
            self.assertIsNone(row["approved_by"])
            self.assertTrue(row["source"] and row["reason"] and row["raw_string_sha256"])


if __name__ == "__main__":
    groups = [CompositionTests] if "--composition" in sys.argv else [ReviewTests] if "--review" in sys.argv else [CompositionTests, ReviewTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group) for group in groups)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
