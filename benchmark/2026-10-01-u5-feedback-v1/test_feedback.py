"""Portable U5 feedback rule controls and SHA-bound static replay tests."""

import csv
import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCANNER = ROOT / "benchmark/2026-09-29-static-wall-prediction"
sys.path.insert(0, str(SCANNER))
from rules_u5_feedback import FAMILIES, SYMBOLS, aarch64_header, app_requirements, dex_family, input_findings, predict
from scan_u5_feedback import FROZEN, FROZEN_SHA, csv_text, dex_facts, file_digest, forecast


def invoke(owner, method, signature="()V"):
    return f"invoke-virtual {{v0}}, L{owner};.{method}:{signature} // method@0001"


def library(name, imports=(), needed=()):
    return dict(path="lib/arm64-v8a/" + name, sha256="1" * 64, bytes=100,
                header="valid-ELF64-AArch64", symbol_status="parsed",
                imports=[dict(name=symbol, weak=False) for symbol in imports], needed=list(needed))


def fixtures():
    facts = dict(entry=dict(key="arbitrary", package="example.test", apk_sha256="a" * 64),
                 metadata_apk_sha256="a" * 64, apks=[dict(path="base.apk", sha256="a" * 64)],
                 selected_apk=dict(sha256="a" * 64), sidecars=[], libraries=[], dex_calls=[], scan_errors=[])
    profile = dict(private_android=library("libandroid.so", needed=["liboh_android_runtime.so"]))
    profile["private_android"]["path"] = "payload/android/lib64/westlake_flutter/libandroid.so"
    return facts, profile


def families(facts, profile):
    return {row["family"] for row in app_requirements(facts, profile)}


class RuleTests(unittest.TestCase):
    def test_dex_positive_and_near_misses(self):
        positives = [
            ("io/flutter/embedding/engine/FlutterJNI", "runBundleAndSnapshotFromLibrary", "()V", "flutter-jni-field-id"),
            ("io/flutter/embedding/engine/FlutterJNI", "nativeRunBundleAndSnapshotFromLibrary", "(J)V", "flutter-jni-field-id"),
            ("android/os/Vibrator", "hasVibrator", "()Z", "vibrator-lock"),
            ("android/os/SystemVibratorManager", "getVibratorIds", "()[I", "vibrator-lock"),
        ]
        for owner, method, signature, family in positives:
            with self.subTest(family=family, method=method):
                instruction = invoke(owner, method, signature)
                self.assertEqual(dex_family(instruction), family)
                self.assertIsNone(dex_family(instruction.replace("invoke-virtual", "const-string")))
                self.assertIsNone(dex_family(instruction.replace(owner, "example/Other")))
                self.assertIsNone(dex_family(instruction.replace(method, method + "Other")))
        self.assertIsNone(dex_family(invoke("android/os/Vibrator", "hasVibrator", "()V")))
        self.assertIsNone(dex_family(invoke("com/google/android/gles_jni/EGLImpl", "eglInitialize", "()Z")))

    def test_private_reload_conjunction_and_key_independence(self):
        facts, profile = fixtures()
        self.assertEqual(families(facts, profile), set())
        facts["dex_calls"] = [dict(instruction=invoke("io/flutter/embedding/engine/FlutterJNI", "runBundleAndSnapshotFromLibrary"))]
        self.assertEqual(families(facts, profile), {"flutter-jni-field-id", "private-runtime-reload"})
        original = app_requirements(facts, profile)
        facts["entry"]["key"] = "a-completely-new-key"
        self.assertEqual(app_requirements(facts, profile), original)
        for row in original:
            self.assertEqual(row["active_wall"], "unknown")
            self.assertEqual(row["startup_reachable"], "unknown")
        profile["private_android"]["needed"] = []
        self.assertEqual(families(facts, profile), {"flutter-jni-field-id"})

    def test_native_strong_consumer_and_weak_controls(self):
        for name, (symbol, family) in SYMBOLS.items():
            facts, profile = fixtures()
            facts["libraries"] = [library(name, [symbol])]
            self.assertEqual(families(facts, profile), {family})
            facts["libraries"][0]["imports"][0]["weak"] = True
            self.assertEqual(families(facts, profile), set())
            facts["libraries"][0] = library("different.so", [symbol])
            self.assertEqual(families(facts, profile), set())
            facts["libraries"][0] = library(name, [symbol + "_other"])
            self.assertEqual(families(facts, profile), set())
            facts["libraries"][0] = library(name, [symbol])
            facts["libraries"][0]["symbol_status"] = "unknown-no-section-table"
            self.assertEqual(families(facts, profile), set())

    def test_realm_needed_not_incidental_strings(self):
        facts, profile = fixtures()
        for name in ["librealm-jni.so", "librealm-jni-10.18.0.so", "librealmc.so"]:
            facts["libraries"] = [library(name, needed=["libz.so"])]
            self.assertEqual(families(facts, profile), {"realm-libz"})
        for name, needed in [("librealm-other.so", ["libz.so"]), ("librealmc.so", ["libz_other.so"])]:
            facts["libraries"] = [library(name, needed=needed)]
            self.assertEqual(families(facts, profile), set())

    def test_all_dex_members_and_failed_tool(self):
        class Process:
            returncode = 0

            def __init__(self, *args, **kwargs):
                self.stdout = io.StringIO("000: |[000] Example.test:()V\n000: |0000: " + invoke("android/os/Vibrator", "hasVibrator", "()Z") + "\n")

            def wait(self):
                return self.returncode

        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "base.apk"
            with zipfile.ZipFile(apk, "w") as archive:
                for name in ["classes.dex", "classes2.dex", "classes7.dex", "classes10.dex", "assets/classes.dex"]:
                    archive.writestr(name, name.encode())
            with patch("scan_u5_feedback.subprocess.Popen", Process):
                inventory, calls = dex_facts(apk, Path("unused"))
                self.assertEqual(len(inventory), 4)
                self.assertEqual(len(calls), 4)
                self.assertTrue(all(row["dex_sha256"] for row in calls))
                Process.returncode = 1
                with self.assertRaisesRegex(ValueError, "dexdump failed"):
                    dex_facts(apk, Path("unused"))


class InputTests(unittest.TestCase):
    def test_three_distinct_categories_and_mono_control(self):
        facts, profile = fixtures()
        facts["dex"] = [f"classes{number}.dex" for number in range(1, 8)]
        self.assertEqual(input_findings(facts), [])
        facts["apks"].append(dict(path="config.apk", sha256="b" * 64))
        facts["metadata_apk_sha256"] = "c" * 64
        facts["sidecars"] = [dict(path="libbad.so", header="wrong-machine")]
        self.assertEqual({row["category"] for row in input_findings(facts)},
                         {"split-key", "non-aarch64-sidecar", "apk-pin-mismatch"})
        self.assertEqual(predict(facts, profile)["app_wall_risks"], [])
        self.assertEqual(predict(facts, profile)["prediction"], "input-blocked-runtime-fixes-insufficient")

    def test_pin_requires_actual_file_even_when_metadata_matches(self):
        facts, _ = fixtures()
        facts["apks"][0]["sha256"] = "b" * 64
        self.assertEqual(input_findings(facts)[0]["category"], "apk-pin-mismatch")

    def test_null_pin_is_unpinned_not_drift(self):
        facts, profile = fixtures()
        facts["entry"]["apk_sha256"] = None
        self.assertEqual(input_findings(facts), [])
        self.assertEqual(predict(facts, profile)["pin_status"], "unpinned-metadata-resolved")
        facts["apks"][0]["sha256"] = "b" * 64
        self.assertEqual(input_findings(facts)[0]["category"], "apk-pin-mismatch")

    def test_elf_header_real_bytes(self):
        header = bytearray(64)
        header[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<HH", header, 16, 3, 183)
        self.assertEqual(aarch64_header(header), "valid-ELF64-AArch64")
        self.assertEqual(aarch64_header(b"PK" + bytes(70)), "invalid-magic")
        self.assertEqual(aarch64_header(header[:20]), "truncated")
        for offset, value, expected in [(4, 1, "wrong-class-or-endian"), (5, 2, "wrong-class-or-endian"),
                                        (18, 62, "wrong-machine"), (16, 2, "not-ET_DYN")]:
            altered = bytearray(header)
            altered[offset] = value
            self.assertEqual(aarch64_header(altered), expected)


class CoverageTests(unittest.TestCase):
    def test_fourteen_static_positive_keys_and_original_runtime_evidence(self):
        document = json.loads((HERE / "static-facts.json").read_text())
        report = forecast(document)
        rows = {row["key"]: row for row in report["rows"]}
        review_root = ROOT / "benchmark/2026-09-30-u4-sweep/j6n4-scoring"
        review = json.loads((review_root / "review.json").read_text())["missed_signatures"]
        self.assertEqual(len(review), 7)
        self.assertEqual(sum(len(row["keys"]) for row in review), 14)
        self.assertEqual(set(FAMILIES), {row["id"] for row in review})
        for family in review:
            for key in family["keys"]:
                with self.subTest(key=key, family=family["id"]):
                    risks = {risk["family"]: risk for risk in rows[key]["app_wall_risks"]}
                    self.assertIn(family["id"], risks)
                    self.assertTrue(risks[family["id"]]["evidence"])
                    text = (review_root / "evidence/logs" / (key + ".json")).read_text()
                    for needle in family["needles"]:
                        self.assertIn(needle, text)
        self.assertIn("not-held-out", report["mode"])

    def test_observed_input_keys_not_counted_as_app_walls(self):
        document = json.loads((HERE / "static-facts.json").read_text())
        rows = {row["key"]: row for row in forecast(document)["rows"]}
        categories = {category: {key for key, row in rows.items() if any(item["category"] == category for item in row["input_findings"])}
                      for category in ["split-key", "non-aarch64-sidecar", "apk-pin-mismatch"]}
        self.assertEqual(categories["split-key"], {"burgerking", "subwaysurfers", "firefox", "mcdonalds", "x"})
        self.assertEqual(categories["non-aarch64-sidecar"], {"fd-seal", "toutiao"})
        self.assertEqual(categories["apk-pin-mismatch"], {"subwaysurfers"})
        self.assertEqual(rows["fd-client"]["input_findings"], [])
        self.assertEqual(len(next(row for row in document["apps"] if row["entry"]["key"] == "fd-client")["dex"]), 7)


class VersionTests(unittest.TestCase):
    def test_wrong_version_and_incomplete_cohort_refused(self):
        document = json.loads((HERE / "static-facts.json").read_text())
        document["version"] = "different"
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            forecast(document)
        document["version"] = "u5-feedback-v1"
        document["apps"].pop()
        with self.assertRaisesRegex(ValueError, "cohort keys"):
            forecast(document)
        document["apps"].append(document["apps"][0])
        with self.assertRaisesRegex(ValueError, "cohort keys"):
            forecast(document)

    def test_replay_and_frozen_csv(self):
        self.assertEqual(file_digest(FROZEN), FROZEN_SHA)
        facts_path = HERE / "static-facts.json"
        document = json.loads(facts_path.read_text())
        expected = forecast(document)
        expected["static_facts_sha256"] = file_digest(facts_path)
        self.assertEqual(json.loads((HERE / "PREDICTIONS.json").read_text()), expected)
        self.assertEqual((HERE / "PREDICTIONS.csv").read_text(), csv_text(expected))
        frozen = {row["key"] for row in csv.DictReader(io.StringIO(FROZEN.read_text()))}
        self.assertEqual(len(expected["rows"]), 66)
        self.assertEqual({row["key"] for row in expected["rows"]}, frozen)
        self.assertTrue(all(row["t20"] == "unpredicted-requires-visual-review" for row in expected["rows"]))
        for relative, expected_sha in json.loads((HERE / "SHA256.json").read_text()).items():
            self.assertEqual(file_digest(ROOT / relative), expected_sha, relative)


if __name__ == "__main__":
    unittest.main()
