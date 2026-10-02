import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from collect import HERE, sha
from stage import candidate_source


def load(name):
    return json.loads((HERE / name).read_text())


class ArchitectureTests(unittest.TestCase):
    def test_pinned_revisions_not_same_architecture(self):
        report = load("architecture.json")
        self.assertEqual([row["commit"][:7] for row in report["commits"]], ["0b5c9af", "1e98162", "c7d2992", "5ae6b75"])
        self.assertFalse(report["framework68_route_A_equivalent"])
        self.assertFalse(report["ledger"]["current_batch_unlock_proof"])
        self.assertIn("route-A media owner registration", report["incomplete"])
        for name, digest in report["upstream_snapshots"].items():
            self.assertEqual(sha(HERE / name), digest)

    def test_play_forwarding_stays_negative(self):
        source = candidate_source()
        self.assertIn("(*p->real)->RegisterCallback(p->real", source)
        self.assertIn("(*PLY(s))->SetCallbackEventsMask", source)
        self.assertNotIn("memcmp(oh_iids[i], id, sizeof(*id))", source)
        self.assertIn("U12EqualAndroidOwnerId", source)


class PrimitiveTests(unittest.TestCase):
    def test_actual_fixture_positive_and_negative(self):
        with tempfile.TemporaryDirectory(prefix="u12-audio-fixture-") as directory:
            executable = str(Path(directory) / "test_adapter")
            command = ["clang", "-std=gnu11", "-D_GNU_SOURCE", "-I" + str(HERE / "inputs"),
                       "-I" + str(HERE), str(HERE / "test_adapter.c"), "-o", executable]
            if sys.platform == "darwin":
                command += ["-Wl,-undefined,dynamic_lookup"]
            else:
                command += ["-ldl", "-pthread"]
            subprocess.run(command, capture_output=True, text=True, check=True)
            result = subprocess.run([executable], capture_output=True, text=True, check=True)
        self.assertIn("IID16/OH IID24", result.stdout)
        self.assertIn("continuous refill8 bytes", result.stdout)
        self.assertIn("NEGATIVE PLAY callbacks/mask=12", result.stdout)

    def test_no_fresh_loader_site(self):
        report = load("evidence/open-candidate.json")
        self.assertEqual(report["binaries"][0]["sites"], [])
        self.assertEqual(report["binaries"][0]["namespace_edges"], [])
        self.assertNotIn("dlopen(", candidate_source())
        self.assertIn("/system/lib64/libOpenSLES.so", candidate_source())


class StaticGateTests(unittest.TestCase):
    def test_export_and_consumer_gate(self):
        report = load("evidence/abi.json")
        self.assertEqual(report["removed"], [])
        self.assertEqual(report["consumer_breaks"], [])
        self.assertEqual(report["call_diffs"], [])
        self.assertEqual(len(report["consumers"]), 7)
        self.assertEqual(report["added"], ["U12BindOpenSLESResidentOwner", "slCreateEngine"])
        receipt = load("build-receipt.json")
        self.assertEqual(receipt["repeated_sha256"][0], receipt["repeated_sha256"][1])

    def test_failed_strings_and_pending_admission_not_hidden(self):
        records = load("architecture.json")["tools"]
        self.assertEqual(next(row for row in records if row["label"] == "strings")["exit_code"], 1)
        self.assertIn("2 dropped, 73 added", (HERE / "evidence/strings.txt").read_text())
        report = load("namespace-gates.json")
        self.assertTrue(report["n2_findings_identical"])
        self.assertFalse(report["rollout_ready"])
        self.assertFalse(report["exception_rebinding_approved"])


if __name__ == "__main__":
    unittest.main()
