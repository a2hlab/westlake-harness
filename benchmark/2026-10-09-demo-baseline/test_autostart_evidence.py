import hashlib
import json
from pathlib import Path
import unittest

import collect_autostart_evidence as audit


class AutostartEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit.collect()

    def test_two_generations_and_published_bytes_match(self):
        first = json.dumps(self.result, sort_keys=True, indent=2) + "\n"
        second = json.dumps(audit.collect(), sort_keys=True, indent=2) + "\n"
        self.assertEqual(first, second)
        self.assertEqual(first, (audit.HERE / "autostart-evidence.json").read_text())

    def test_exact_signed_counts(self):
        self.assertEqual(self.result["summary"], {
            "mounts": 56, "groups": {"shared": 51, "zigzag-private": 5},
            "kinds": {"directory": 3, "file": 53}, "baseline_targets": 319,
            "source_members": 313, "data_source_members": 306,
            "unmounted_system_members": 7,
        })
        self.assertEqual(self.result["journal_sha256"],
                         "f24718730ccd4165d876a411daf0d717630311de0ac2a1c5b1c20923c8ebde67")
        self.assertEqual(self.result["host_sha256"],
                         "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e")

    def test_directory_layers_precede_children(self):
        rows = self.result["layers"]
        self.assertEqual([row["sequence"] for row in rows], list(range(1, 57)))
        for parent in rows:
            for child in rows:
                if child["target"].startswith(parent["target"] + "/"):
                    self.assertLess(parent["sequence"], child["sequence"])
        self.assertEqual(len({row["target"] for row in rows}), 56)

    def test_declared_cleanup_and_zero_execution(self):
        self.assertEqual(self.result["candidate_additions_to_clean"],
                         ["/system/android/lib64/libicu74compat.so"])
        self.assertFalse(self.result["execution_enabled"])
        self.assertFalse(self.result["board_access"])
        self.assertEqual(self.result["journal_status"], "active_verified")

    def test_source_resolution_matches_every_expected_byte(self):
        for target, expected_sha in self.result["expected"].items():
            source = target
            for row in self.result["layers"]:
                if target == row["target"] or target.startswith(row["target"] + "/"):
                    source = row["source"] + target[len(row["target"]):]
            self.assertEqual(self.result["source_hashes"][source], expected_sha)

    def test_primary_sources_are_portable_and_pinned(self):
        self.assertEqual(len(self.result["sources"]), 13)
        for source in self.result["sources"]:
            path = source["path"]
            self.assertTrue(path.startswith(("$WORKSPACES/", "$ORCA/")))
            expanded = path.replace("$WORKSPACES/", str(audit.WORKSPACES) + "/", 1)
            expanded = expanded.replace("$ORCA/", str(audit.ORCA) + "/", 1)
            self.assertEqual(hashlib.sha256(Path(expanded).read_bytes()).hexdigest(),
                             source["sha256"])
        sibling = audit.WORKSPACES / "westlake-harness-u7-executor/example"
        self.assertEqual(audit.portable(sibling),
                         "$WORKSPACES/westlake-harness-u7-executor/example")


if __name__ == "__main__":
    unittest.main()
