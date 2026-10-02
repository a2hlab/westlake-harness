import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from common import HERE, OLD, sha
from oracle import table_from_source


def load(name):
    return json.loads((HERE / name).read_text())


class NativeTests(unittest.TestCase):
    def test_exact_baseline_and_single_export(self):
        receipt = load("build-receipt.json")
        self.assertTrue(receipt["baseline_reproduced"])
        self.assertTrue(receipt["same_bytes"])
        self.assertEqual(receipt["repeated"][0], receipt["repeated"][1])
        self.assertEqual(receipt["repeated"][0]["baseline"], OLD)
        self.assertEqual(receipt["added_exports"], ["_ctype_"])
        abi = load("evidence/abi-b2.json")
        self.assertEqual(abi["added"], ["_ctype_"])
        for name in ["removed", "drift", "call_diffs", "consumer_breaks"]:
            self.assertFalse(abi[name], name)
        self.assertEqual(load("consumer-set.json")["count"], 219)

    def test_original_sources_and_table(self):
        source = load("sources.json")
        for row in source["sources"]:
            self.assertEqual(sha(HERE / row["snapshot"]), row["sha256"])
        self.assertEqual(sha(HERE / "ctype_compat.c"), source["candidate_source_sha256"])
        base = HERE / "inputs/aosp"
        table, values = table_from_source((base / "libc/upstream-openbsd/lib/libc/gen/ctype_.c").read_text(),
            (base / "libc/include/bits/ctype_inlines.h").read_text(),
            (base / "libc/upstream-openbsd/android/include/openbsd-compat.h").read_text())
        proof = load("table-proof.json")
        self.assertEqual(list(table), proof["table"]["bytes"])
        self.assertEqual(proof["pointer"]["size"], 8)
        self.assertEqual(proof["table"]["binding"], "LOCAL")
        self.assertEqual(values["_N"], 4)
        self.assertEqual(table[ord("0") + 1], 4)
        self.assertEqual(table[ord("A") + 1], 65)
        self.assertEqual(table[33], 136)
        self.assertEqual(table[10], 40)
        self.assertEqual(table[129:], bytes(128))

    def test_landed_source_compiles_without_artifacts(self):
        compiler = shutil.which("clang") or shutil.which("cc")
        if not compiler:
            self.skipTest("No native C compiler available; source compile is not claimed")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "ctype-test"
            subprocess.run([compiler, "-std=c11", "-I" + str(HERE / "inputs/shim"),
                "-I" + str(HERE / "inputs/aosp/libc/upstream-openbsd/lib/libc/include"),
                str(HERE / "test_table.c"), "-o", str(target)], check=True, capture_output=True)
            output = subprocess.check_output([target], text=True).strip()
            self.assertEqual(list(bytes.fromhex(output)), load("table-oracle.json")["bytes"])

    def test_unexpected_table_token_rejected(self):
        with self.assertRaises(ValueError):
            table_from_source("broken source", "", "")

    def test_static_sites_keep_raw_diagnostic(self):
        old = load("evidence/open-b2.json")["binaries"][0]
        new = load("evidence/open-candidate.json")["binaries"][0]
        self.assertEqual(len(old["sites"]), 2)
        self.assertEqual(len(new["sites"]), 2)
        self.assertEqual(old["namespace_edges"], new["namespace_edges"])
        self.assertIn("unknown:x1 clobbered by call at 0x3b98", (HERE / "evidence/open-candidate.txt").read_text())
        strings = load("strings-review.json")
        self.assertEqual((strings["dropped"], strings["added"]), (0, 1))
        self.assertTrue(strings["rows"][0]["exact_table_projection"])
        self.assertIsNone(strings["approved_by"])


class DraftTests(unittest.TestCase):
    def test_disabled_atomic_rebind(self):
        composition = load("composition.json")
        manifest = load("manifests/native-manifest.json")
        bundle = load("manifests/bundle-manifest.json")
        self.assertEqual(sha(HERE / "manifests/native-manifest.json"), composition["native_manifest_sha256"])
        self.assertEqual(sha(HERE / "manifests/bundle-manifest.json"), composition["bundle_sha256"])
        members = composition["changed_payload_members"]
        self.assertEqual(len(members), 2)
        self.assertTrue(all(name.endswith("/libbionic_compat.so") for name in members))
        self.assertEqual([manifest["files"][name] for name in members], [composition["compat_after"]] * 2)
        self.assertEqual(manifest["files"]["payload/runtime/appspawn-x"], composition["host_sha256"])
        self.assertFalse(bundle["rollout_ready"])
        self.assertFalse(manifest["rollout_ready"])
        self.assertNotIn("window_authorization", manifest)
        self.assertNotIn("window_authorization", bundle)

    def test_inventory_is_not_observed_unlock(self):
        prediction = load("predictions.json")
        self.assertEqual(prediction["proven_first_fatal_moves"], 0)
        self.assertEqual(prediction["conditional_first_fatal_moves"], 1)
        row = prediction["rows"][0]
        self.assertEqual(row["key"], "mcdonalds")
        self.assertEqual(row["predicted_t20"], "unknown")
        self.assertFalse(row["host_candidate_included"])
        consumer = load("realmc-consumer.json")
        self.assertEqual(consumer["strong_import_count"], len(consumer["rows"]))
        self.assertTrue(any(row["import_name"] == "_ctype_@LIBC" for row in consumer["rows"]))

    def test_no_fabricated_gate_approval(self):
        gate = load("namespace-gates.json")
        self.assertEqual(gate["candidate_status"], "REJECT")
        self.assertTrue(gate["registry_unchanged"])
        self.assertFalse(gate["exceptions_applied"])
        review = load("outer-review.json")
        self.assertIsNone(review["approved_by"])
        for row in load("registry-delta.draft.json")["exceptions"]:
            self.assertIsNone(row["approved_by"])
            self.assertIsNone(row["approved_at"])
            for path in row["evidence"]:
                self.assertTrue((HERE.parents[1] / path).is_file())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["native", "draft", "all"], default="all")
    args, rest = parser.parse_known_args()
    classes = {"native": [NativeTests], "draft": [DraftTests], "all": [NativeTests, DraftTests]}[args.part]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(item) for item in classes)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
