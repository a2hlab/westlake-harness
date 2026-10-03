import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from validation import COMPILER, DRIVER, check_actual_pair, check_admission, check_atomic, check_pair_template, check_preview


HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class BindingTests(unittest.TestCase):
    def test_204_actual_mappings_and_evidence(self):
        check_preview(load("registry-delta.preview.json"), load("old-partial-final-mapping.json"))
        self.assertFalse(load("active-inputs-unchanged.json")["writes"])
        self.assertEqual(load("active-inputs-unchanged.json")["before"], load("active-inputs-unchanged.json")["after"])

    def test_semantic_or_final_hash_drift_rejected(self):
        preview = load("registry-delta.preview.json")
        mapping = load("old-partial-final-mapping.json")
        mapping[0]["semantic_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "semantics"):
            check_preview(preview, mapping)
        preview["final_manifest_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            check_preview(preview, load("old-partial-final-mapping.json"))

    def test_split_host_anl_alias_rejected(self):
        files = load("evidence/atomic-files.json")
        check_atomic(files)
        for name in files:
            changed = dict(files)
            changed.pop(name)
            with self.assertRaisesRegex(ValueError, "atomic pair"):
                check_atomic(changed)

    def test_flutter_replacement_needs_no_new_row(self):
        decision = load("flutter-admission-decision.json")
        check_admission(decision)
        decision["new_native_row_required"] = True
        with self.assertRaisesRegex(ValueError, "No new-native"):
            check_admission(decision)

    def test_strings_approval_is_exact_and_separate(self):
        signed = load("evidence/outer-approval-strings.json")
        self.assertEqual(signed["signer"], "outer(claude)")
        self.assertEqual(signed["decision"], "approve all 20 rows")
        self.assertIn("ship together", signed["condition"])
        self.assertIn("b6b466d7ac5dc65b5ee50fd5ee96e0c395f816b496949613659c0ddac572bde9", signed["object"])


class PairTests(unittest.TestCase):
    def test_pair_is_two_complete_unexecuted_maps(self):
        expected = load("expected-pair.json")
        check_pair_template(load("paired-receipt.template.json"), expected["inputs"], expected["images"])
        arrival = load("assembly-arrival.json")
        self.assertEqual(arrival["transaction_base"], {"common": None, "61b": None})
        for field in ["final_bundle_sha256", "final_native_manifest_sha256", "final_inputs_sha256"]:
            self.assertIsNone(arrival[field])
        self.assertIsNone(arrival["runtime_jar"]["sha256"])
        self.assertFalse(arrival["runtime_jar"]["in_bcp"])

    def test_incomplete_or_fabricated_template_is_rejected(self):
        expected = load("expected-pair.json")
        pair = load("paired-receipt.template.json")
        pair["runs"][0]["outputs"].pop(expected["images"][0])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            check_pair_template(pair, expected["inputs"], expected["images"])
        pair = load("paired-receipt.template.json")
        pair["runs"][0]["session_tee_exit_code"] = 0
        with self.assertRaisesRegex(ValueError, "fabricated"):
            check_pair_template(pair, expected["inputs"], expected["images"])

    def test_actual_pair_failures_and_old_approval(self):
        expected = load("expected-pair.json")
        argv = ["synthetic-test-only"]
        row = dict(input_jars=expected["inputs"], outputs={name: "a" * 64 for name in expected["images"]},
            dex2oat_sha256=COMPILER, driver_sha256=DRIVER, actual_argv=argv,
            argv_sha256=hashlib.sha256(json.dumps(argv, separators=(",", ":")).encode()).hexdigest(),
            toolchain_identity_sha256="b" * 64, hostlibs_sha256="c" * 64, build_log_sha256="d" * 64,
            session_log_sha256="e" * 64, dex2oat_exit_code=0, tee_exit_code=0, session_tee_exit_code=0,
            script_exit_code=0, frozen_driver_exit_code=6, exception_used=False)
        pair = dict(status="verified", runs=[dict(row, run=1), dict(row, run=2)])
        check_actual_pair(pair, expected["inputs"], expected["images"])
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            changed = copy.deepcopy(pair)
            changed["runs"][1][field] = 1
            with self.assertRaisesRegex(ValueError, "logging"):
                check_actual_pair(changed, expected["inputs"], expected["images"])
        changed = copy.deepcopy(pair)
        changed["runs"][1]["exception_used"] = True
        changed["runs"][1]["u14_outer_exception_approval"] = {"sha256": "a" * 64}
        with self.assertRaisesRegex(ValueError, "historical exception"):
            check_actual_pair(changed, expected["inputs"], expected["images"])


if __name__ == "__main__":
    groups = [BindingTests] if "--bindings" in sys.argv else [PairTests] if "--pair" in sys.argv else [BindingTests, PairTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(group) for group in groups)
    raise SystemExit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
