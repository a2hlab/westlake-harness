import argparse
import copy
import hashlib
import json
from pathlib import Path
import unittest

from rebind import draft_native_rows, draft_static_policy, digest

HERE = Path(__file__).resolve().parent
EVIDENCE = "benchmark/2026-10-03-u13-gate-review/evidence/native-final.json"


def load(name):
    return json.loads((HERE / name).read_text())


class ProofTests(unittest.TestCase):
    def test_all_instruction_semantics_match(self):
        proof = load("semantics.json")
        bodies = proof["bodies"]
        self.assertEqual(bodies["old"]["normalized"], bodies["vlc"]["normalized"])
        self.assertEqual(bodies["old"]["normalized"], bodies["new"]["normalized"])
        self.assertEqual({body["instruction_count"] for body in bodies.values()}, {33})
        self.assertEqual(int(bodies["vlc"]["backend_pc"], 16) - int(bodies["old"]["backend_pc"], 16), 0x300)
        self.assertEqual(int(bodies["new"]["backend_pc"], 16) - int(bodies["old"]["backend_pc"], 16), 0x440)
        for body in bodies.values():
            self.assertFalse(body["backend_can_reach_fallback"])
            references = body["references"]
            self.assertEqual({row["symbol"] for row in references if row["kind"] == "GOT"},
                {"__loader_android_dlopen_ext", "stderr"})
            constants = {row["value"] for row in references if row["kind"] == "cstring"}
            self.assertIn("(null)", constants)
            self.assertTrue(any(value.startswith("[U10-DLEXT] backend absent;") for value in constants))
        overlay = HERE / "sources/android_dlopen_ext.c"
        self.assertEqual(hashlib.sha256(overlay.read_bytes()).hexdigest(), proof["source_sha256"])

    def test_original_source_and_full_gfx_coverage(self):
        lineage = load("lineage.json")
        for row in lineage["comparisons"]:
            self.assertTrue(row["unchanged_statement"])
        self.assertTrue(lineage["old_full_gfx_absent"])
        self.assertFalse(lineage["resident_availability_proven"])
        self.assertEqual(hashlib.sha256((HERE / "sources/gfx-old.cpp").read_bytes()).hexdigest(), lineage["baseline_source_sha256"])
        self.assertEqual(hashlib.sha256((HERE / "sources/gfx-new.cpp").read_bytes()).hexdigest(), lineage["candidate_source_sha256"])
        self.assertEqual(len(lineage["runtime_sites"]), 4)
        self.assertTrue(all(site["flags"] == ["0x6=NOW|NOLOAD"] for site in lineage["runtime_sites"]))
        self.assertIn("no retry", lineage["miss_behavior"]["egl"])

    def test_factory_binary_no_new_mapping_guard(self):
        flags = load("evidence/noload-flags.json")
        self.assertTrue(flags["factory_libc_sha256"].startswith("fd3c4701"))
        self.assertFalse(flags["same_source_provenance"])
        mode = (HERE / "evidence/noload-mode.txt").read_text()
        guard = (HERE / "evidence/noload-map-guard.txt").read_text()
        self.assertIn("85dc4:", mode)
        self.assertIn("and\tw9, w19, #0x4", mode)
        self.assertIn("87134:", guard)
        self.assertIn("cbnz\tw8, 0x8717c", guard)
        self.assertIn("87140:", guard)


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.report = load("evidence/native-final.json")
        self.manifest = (HERE / "manifests/native-manifest.json").read_bytes()
        self.inputs = (HERE / "manifests/native-inputs.json").read_bytes()

    def test_pending_rows_cannot_authorize(self):
        rows = draft_native_rows(self.report, self.manifest, self.inputs, EVIDENCE)
        self.assertEqual(len(rows["exceptions"]), 2)
        for row in rows["exceptions"]:
            self.assertIsNone(row["approved_by"])
            self.assertIsNone(row["approved_at"])
            self.assertEqual(row["gate"], "N1")
            for evidence in row["evidence"]:
                self.assertTrue((HERE.parents[1] / evidence).is_file())
        static = draft_static_policy(load("static-review.json"), hashlib.sha256(self.manifest).hexdigest())
        self.assertEqual(len(static["native"]), 2)
        self.assertFalse(static["execution_enabled"])
        self.assertTrue(all(row["approved_by"] is None for row in static["native"].values()))

    def test_stale_manifest_rejected(self):
        manifest = json.loads(self.manifest)
        manifest["variant"] += " changed"
        with self.assertRaisesRegex(ValueError, "Stale report"):
            draft_native_rows(self.report, json.dumps(manifest).encode(), self.inputs, EVIDENCE)

    def test_stale_inputs_or_bad_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError, "Stale report"):
            draft_native_rows(self.report, self.manifest, self.inputs + b" ", EVIDENCE)
        with self.assertRaisesRegex(ValueError, "does not exist"):
            draft_native_rows(self.report, self.manifest, self.inputs, "benchmark/missing-report.json")

    def test_changed_pair_or_delta_rejected(self):
        review = copy.deepcopy(load("static-review.json"))
        review["review_required"][0]["candidate_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            draft_static_policy(review, "0" * 64)
        review = copy.deepcopy(load("static-review.json"))
        review["review_required"][0]["delta_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            draft_static_policy(review, "0" * 64)

    def test_fresh_binding_changes_ids_not_approval(self):
        previous = draft_native_rows(self.report, self.manifest, self.inputs, EVIDENCE)
        manifest = json.loads(self.manifest)
        manifest["variant"] += " fresh identity"
        updated = json.dumps(manifest).encode()
        fresh = copy.deepcopy(self.report)
        fresh["package_manifest_sha256"] = hashlib.sha256(updated).hexdigest()
        for source in fresh["gates"]["N1"]["findings"]:
            finding = {key: value for key, value in source.items() if key not in {"issue_id", "disposition", "exception", "gate"}}
            source["issue_id"] = digest(dict(gate="N1", package_manifest_sha256=fresh["package_manifest_sha256"],
                inputs_sha256=fresh["inputs_sha256"], finding=finding))
        rows = draft_native_rows(fresh, updated, self.inputs, EVIDENCE)
        self.assertNotEqual([row["issue_id"] for row in previous["exceptions"]], [row["issue_id"] for row in rows["exceptions"]])
        self.assertTrue(all(row["approved_by"] is None for row in rows["exceptions"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["proof", "drafts", "all"], default="all")
    args = parser.parse_args()
    classes = {"proof": [ProofTests], "drafts": [DraftTests], "all": [ProofTests, DraftTests]}[args.part]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(item) for item in classes)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
