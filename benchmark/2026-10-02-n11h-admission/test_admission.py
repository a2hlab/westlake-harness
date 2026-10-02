import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import compat_readout
import package
from settings import ACCEPTED, ARTIFACTS, BASE_SHA, HERE, HOST_SHA, MANIFEST_SHA, INPUTS_SHA, candidate_report, file, load, sha
import timing


def hilog(message, pid=71, tid=72):
    return "10-02 12:00:00.000 " + str(pid) + " " + str(tid) + " I APPSPAWN: [U10-COMPAT-VISIBLE] " + message


VERIFIED = "owner_verified view=westlake.sealed.child resident_view=westlake.sealed.child abort=0x11 getter=0x12 gnu=0x13 inheritance=caller_owned"
UNAVAILABLE = "unavailable unmapped resident compat; no loading fallback; namespace continues"


class TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = timing.replay()["cases"]

    def test_late_counterexample(self):
        old, new = self.result["r3"]["late"], self.result["n11h"]["late"]
        self.assertLess(old["bootstrap_sequence"], old["first_compat_query"])
        self.assertLess(new["first_compat_query"], new["bootstrap_sequence"])
        self.assertEqual((old["verified"], new["unavailable"]), (1, 1))
        self.assertEqual((old["app_compat_edges"], new["app_compat_edges"]), (1, 0))
        self.assertTrue(any(" -> westlake.sealed.child libbionic_compat.so" in line for line in old["trace"]))

    def test_other_branches_nonfatal(self):
        for variant in self.result.values():
            self.assertTrue(all(row["callback_rc"] == 0 for row in variant.values()))
            self.assertEqual(variant["early"]["verified"], 1)
            self.assertEqual(variant["absent"]["unavailable"], 1)
        self.assertEqual(self.result["r3"]["private"]["compat_queries"], 2)
        self.assertEqual(self.result["n11h"]["private"]["compat_queries"], 0)
        self.assertEqual(self.result["n11h"]["private"]["app_compat_edges"], 2)

    def test_accepted_bytes_unchanged(self):
        self.assertEqual(sha(ARTIFACTS / "baseline/appspawn-x"), BASE_SHA)
        self.assertEqual(sha(ARTIFACTS / "candidate/appspawn-x"), HOST_SHA)
        self.assertEqual(candidate_report()["package_manifest_sha256"], MANIFEST_SHA)


class SmokeTests(unittest.TestCase):
    def check_state(self, messages, expected, **scope):
        result = compat_readout.classify(messages, 71, **scope)
        self.assertEqual(result["state"], expected)
        self.assertIsNone(result["compat_success"])
        self.assertIsNone(result["smoke_verdict"])
        self.assertIsNone(result["relocation_success"])
        self.assertFalse(result["smoke_failure_from_this_readout"])
        return result

    def test_verified_not_relocation(self):
        self.assertTrue(self.check_state([hilog(VERIFIED)], "QUERY_VERIFIED")["query_verified"])

    def test_all_unavailable_variants(self):
        for message in [UNAVAILABLE, "unavailable missing resident namespace; no loading fallback; namespace continues",
                        "unavailable result=8; no loading fallback; namespace continues"]:
            self.assertFalse(self.check_state([hilog(message)], "QUERY_UNAVAILABLE")["query_verified"])

    def test_inherit_failure_dominates(self):
        self.check_state([hilog(VERIFIED), hilog("unavailable inherit result=2; namespace continues")], "INHERIT_UNAVAILABLE")

    def test_pid_tid_scope_and_absence(self):
        self.check_state([hilog(VERIFIED, pid=73)], "UNOBSERVED")
        self.check_state([hilog(VERIFIED)], "UNOBSERVED", tid=99)
        self.check_state([], "UNOBSERVED")

    def test_declared_skip_not_success(self):
        for branch in ["private", "no-bridge"]:
            self.check_state([], "SKIPPED_DECLARED_BRANCH", branch=branch)
            self.check_state([hilog(VERIFIED)], "MIXED_OR_MALFORMED", branch=branch)

    def test_mixed_malformed_and_null(self):
        for lines in [[hilog(VERIFIED), hilog(UNAVAILABLE)], ["[U10-COMPAT-VISIBLE] " + VERIFIED],
                      [hilog("owner_verified")], [hilog(VERIFIED.replace("abort=0x11", "abort=0x0"))]]:
            self.check_state(lines, "MIXED_OR_MALFORMED")

    def test_cli_unavailable_exit_not_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "hilog.txt"
            path.write_text(hilog(UNAVAILABLE) + "\n")
            command = [sys.executable, str(HERE / "compat_readout.py"), "--hilog", str(path), "--pid", "71"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["state"], "QUERY_UNAVAILABLE")
            invalid = subprocess.run(command[:-1] + ["0"], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)

    def test_rule_not_smoke_execution_spec(self):
        rule = load(compat_readout.RULE)
        self.assertEqual(rule["host_sha256"], HOST_SHA)
        self.assertNotIn("groups", rule)
        self.assertNotIn("fixes", rule)
        self.assertFalse(rule["smoke_integration"]["unavailable_counts_compat_success"])


class StringsTests(unittest.TestCase):
    def test_exact_delta_and_unchecked_sources(self):
        review, raw = package.string_review(), package.raw_strings()
        actual = {(row["direction"], row["value_sha256"]) for row in review["items"]}
        expected = {(direction, hashlib.sha256(value.encode()).hexdigest()) for direction, values in raw.items() for value in values}
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 19)
        for row in review["items"]:
            self.assertFalse(row["outer_checked"])
            self.assertEqual(row["decision"], "PENDING")
            for witness in row["source"]:
                path = file(witness["path"])
                self.assertEqual(sha(path), witness["sha256"])
                self.assertEqual(path.read_text().splitlines()[witness["line"] - 1].strip(), witness["text"])

    def test_unknown_extra_string_rejected(self):
        raw = package.raw_strings()
        raw["ADDED"].add("UNREVIEWED_SEARCH_PATH")
        with patch.object(package, "raw_strings", return_value=raw):
            with self.assertRaises((ValueError, KeyError)):
                package.string_review()

    def test_generated_checklist_binding(self):
        self.assertEqual(load(str(HERE.relative_to(file(ACCEPTED + "/README.md").parents[2])) + "/strings-allow.json"), package.string_review())
        checklist = (HERE / "STRINGS-CHECKLIST.md").read_text()
        self.assertEqual(checklist.count("- [ ] **"), 19)
        self.assertNotIn("- [x]", checklist)


class ExceptionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deltas, cls.review, cls.proof = package.exceptions("2026-10-02T00:00:00+08:00")

    def test_counts_bindings_sources(self):
        candidate = candidate_report()
        self.assertEqual(len(self.deltas["N2"]["exceptions"]), 103)
        self.assertEqual(len(self.deltas["N1"]["exceptions"]), 53)
        for gate, delta in self.deltas.items():
            findings = {row["issue_id"]: row for row in candidate["gates"][gate]["findings"]}
            for row in delta["exceptions"]:
                self.assertEqual(row["package_manifest_sha256"], MANIFEST_SHA)
                self.assertEqual(row["inputs_sha256"], INPUTS_SHA)
                self.assertEqual(row["issue_id"], package.identity(gate, candidate, findings[row["issue_id"]]))
                for name in row["evidence"]:
                    self.assertTrue(file(name).is_file())
                    self.assertNotEqual(name, "benchmark/2026-10-02-u10-1-t8-rerun/native-gate.json")

    def test_new_query_never_autoapproved(self):
        self.assertEqual(self.review["state"], "PENDING_OUTER_REVIEW")
        self.assertNotIn("approved_by", self.review)
        self.assertFalse(self.review["outer_checked"])
        self.assertEqual(self.review["finding"]["detail"]["evidence"]["line"], 29)
        self.assertEqual(self.proof["simulation"]["N2-only"]["N1"]["rejected"], 54)
        combined = self.proof["simulation"]["N2-and-existing-N1"]
        self.assertEqual((combined["N1"]["rejected"], combined["N2"]["rejected"]), (1, 0))
        self.assertEqual(combined["N1"]["rejected_ids"], [self.review["issue_id"]])
        self.assertFalse(self.proof["live_registry_modified"])

    def test_mutated_finding_binding_rejected(self):
        changed = copy.deepcopy(candidate_report())
        changed["gates"]["N2"]["findings"][0]["expression"] = "drift"
        with patch.object(package, "candidate_report", return_value=changed):
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                package.exceptions("test")

    def test_missing_evidence_rejected(self):
        original = package.file
        def missing(name):
            if name == "benchmark/2026-10-02-u10-1-t8-rerun/approved-native-gate.json":
                raise ValueError("missing existing evidence")
            return original(name)
        with patch.object(package, "file", side_effect=missing):
            with self.assertRaisesRegex(ValueError, "missing existing evidence"):
                package.exceptions("test")

    def test_semantic_ignore_is_line_only(self):
        sample = dict(detail=dict(evidence=dict(source="owner.c", line=29, text="NOLOAD")))
        relocated = copy.deepcopy(sample)
        relocated["detail"]["evidence"]["line"] = 30
        self.assertEqual(package.body(sample, True), package.body(relocated, True))
        relocated["detail"]["evidence"]["text"] = "FRESH"
        self.assertNotEqual(package.body(sample, True), package.body(relocated, True))


if __name__ == "__main__":
    unittest.main()
