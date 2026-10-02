import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import audit
import stats


def load(name):
    return json.loads((audit.HERE / name).read_text())


class IdentityTests(unittest.TestCase):
    def test_pinned_deployed_bytes(self):
        self.assertEqual(audit.sha(audit.BINARIES["old"]), audit.OLD)
        self.assertEqual(audit.sha(audit.BINARIES["new"]), audit.NEW)
        result = load("evidence/abi.json")
        for field in ["removed", "added", "drift", "consumer_breaks"]:
            self.assertEqual(result[field], [])
        self.assertEqual(result["old"]["sha256"], audit.OLD)

    def test_entries_and_static_scope(self):
        self.assertIn("0xc7a14", (audit.HERE / "evidence/entry-old.txt").read_text())
        self.assertIn("0xc8a14", (audit.HERE / "evidence/entry-new.txt").read_text())
        report = load("artifacts.json")
        self.assertEqual(len({json.dumps(row, sort_keys=True) for row in report["section_identity"].values()}), 1)
        self.assertIn("NOT service absence", report["whois_scope"])
        self.assertEqual(next(row for row in report["commands"] if row["label"] == "strings")["exit_code"], 1)
        self.assertTrue(load("evidence/open-delta.json")["semantic_equal"])


class PolicyTests(unittest.TestCase):
    def test_compiled_table_and_mutations(self):
        table = audit.compiled_table()
        self.assertEqual(len(table), 4)
        fields = ["bundle", "abi", "filename", "sha256"]
        exact = {tuple(row[field] for field in fields) for row in table}
        for row in table:
            for field in fields:
                mutated = copy.deepcopy(row)
                mutated[field] += "-changed"
                self.assertNotIn(tuple(mutated[name] for name in fields), exact)
        self.assertNotIn("apk_sha256", table[0])

    def test_default_guards_retained(self):
        source = (audit.KIT / "candidate-source" / audit.SOURCE).read_text()
        for needle in ["static_cast<uint32_t>(crc) == entry.crc && checkPayload(path, name)", "!S_ISREG(fileStat.st_mode)",
                       "fileStat.st_uid != 0 || fileStat.st_gid != 0", "entry.uncompressedSize", "if (checkElf(path))", "Sha256File(path) == exception.sha256"]:
            self.assertIn(needle, source)
        changes = load("evidence/rodata-delta.json")
        self.assertEqual(len(changes["dropped"]), 1)
        self.assertEqual(len(changes["added"]), 12)


class StatsTests(unittest.TestCase):
    def test_selected_and_diagnostic_counts(self):
        result = stats.collect()
        self.assertEqual(len(result["selected"]), 166)
        self.assertEqual(sum(row["accepted"] for row in result["signed_other165"].values()), 165)
        self.assertEqual(result["additional_diagnostic_attempts"]["5ea34a45"]["rejected"], 3)
        for row in result["selected"] + result["additional"]:
            for evidence in row["evidence"]:
                path = evidence["path"].replace("$WORKSPACES", str(audit.WS))
                self.assertEqual(audit.sha(path), evidence["sha256"])

    def test_missing_and_rc_zero_failure(self):
        self.assertEqual(stats.outcome({}, ""), "unknown")
        failed = dict(install=dict(return_code=0, success_text=False))
        self.assertEqual(stats.outcome(failed, "error: failed to install bundle. code:9568260 install internal error."), "rejected")
        self.assertEqual(stats.outcome(failed, "nonterminal warning"), "unknown")
        self.assertEqual(stats.outcome(failed, "error: failed to install bundle\ninstall bundle successfully."), "unknown")

    def test_master_prefix_does_not_corrupt_selected_evidence(self):
        with patch.object(audit, "REPO", audit.WS / "westlake-harness"):
            self.test_selected_and_diagnostic_counts()


class PortableTests(unittest.TestCase):
    def test_five_helpers_under_master_and_lane_roots(self):
        helpers = [("2026-10-02-libinstalls-unification", "audit.py"),
                   ("2026-10-02-toutiao-bionic-scope", "audit.py"),
                   ("2026-10-02-u12-disappeared", "collect.py"),
                   ("2026-10-02-u12-sigabrt", "collect.py"),
                   ("2026-10-02-u12-upstream-audio", "collect.py")]
        for number, (directory, filename) in enumerate(helpers):
            spec = importlib.util.spec_from_file_location("portable_fixture_" + str(number), audit.HERE.parent / directory / filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for repository in [audit.WS / "westlake-harness", audit.WS / "westlake-harness-bms"]:
                with self.subTest(helper=directory, repository=repository.name), patch.object(module, "REPO", repository):
                    sibling = audit.WS / "westlake-harness-u7-executor/benchmark/run/aegis/record.json"
                    self.assertEqual(module.portable(sibling), "$WORKSPACES/westlake-harness-u7-executor/benchmark/run/aegis/record.json")
                    self.assertEqual(module.portable(repository / "benchmark/local.json"), "$REPO/benchmark/local.json")
                    self.assertEqual(module.portable(repository), "$REPO")
                    embedded = 'path="' + str(sibling) + '"'
                    self.assertIn("$WORKSPACES/westlake-harness-u7-executor/", module.portable(embedded))


class PlanTests(unittest.TestCase):
    def test_only_two_boards_two_aliases(self):
        result = stats.plan()
        self.assertFalse(result["execution_enabled"])
        self.assertFalse(result["device_access"])
        self.assertEqual([row["board"] for row in result["operations"]], [stats.SERIALS["5ea"], stats.SERIALS["5cd"]])
        for row in result["operations"]:
            self.assertEqual(row["rollback_sha256"], audit.OLD)
            self.assertEqual(row["expected_after_sha256"], audit.NEW)
            self.assertEqual(len(row["paths"]), 2)
        self.assertEqual(result["already_target"]["board"], stats.SERIALS["61b"])
        self.assertTrue(result["expect"]["confirm"] and result["expect"]["refute"])

    def test_actual_offline_dry_run(self):
        for board in ["5ea", "5cd"]:
            result = load("evidence/transaction-dry-run-" + board + ".txt")
            self.assertFalse(result["device_io"])
            self.assertEqual(len(result["paths"]), 2)
            self.assertEqual(result["candidate_sha256"], {"libinstalls.z.so": audit.NEW})


if __name__ == "__main__":
    unittest.main()
