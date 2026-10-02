import argparse
import copy
import json
from pathlib import Path
import unittest

from common import COMPAT, HERE, HOST, POLICY, assert_disabled, portable, sha


class DisabledTests(unittest.TestCase):
    def setUp(self):
        self.data = dict(rollout_ready=False)
        self.manifest = dict(rollout_ready=False, files={"payload/runtime/appspawn-x": HOST})
        for name, digest in [("libbionic_compat.so", COMPAT), ("libnativeloader.so", POLICY)]:
            for directory in ["android/lib64", "route"]:
                self.manifest["files"]["payload/" + directory + "/" + name] = digest

    def test_disabled_acceptance(self):
        assert_disabled(self.data, self.manifest)
        self.data["rollout_ready"] = True
        with self.assertRaises(ValueError):
            assert_disabled(self.data, self.manifest)
        self.data["rollout_ready"] = False
        self.data["window_authorization"] = "not accepted"
        with self.assertRaises(ValueError):
            assert_disabled(self.data, self.manifest)

    def test_held_host(self):
        self.manifest["files"]["payload/runtime/appspawn-x"] = "c2883376"
        with self.assertRaises(ValueError):
            assert_disabled(self.data, self.manifest)

    def test_split_aliases(self):
        self.manifest["files"]["payload/route/libbionic_compat.so"] = "015aa3a6"
        with self.assertRaises(ValueError):
            assert_disabled(self.data, self.manifest)

    def test_external_worktree_prefix(self):
        from common import WORKSPACES
        external = WORKSPACES / "westlake-harness-bms-deploy/a.txt"
        self.assertEqual(portable(external), "$WORKSPACES/westlake-harness-bms-deploy/a.txt")


class EvidenceTests(unittest.TestCase):
    def load(self, name):
        return json.loads((HERE / name).read_text())

    def test_full_inventory(self):
        report = self.load("full-package-open-sites.json")
        self.assertEqual(report["target_count"], len(report["targets"]))
        self.assertEqual(report["target_count"], 116)
        self.assertEqual(report["unique_elf_count"], len(report["scans"]))
        self.assertEqual(len({row["target"] for row in report["targets"]}), 116)
        for row in report["targets"]:
            for field in ["before", "after"]:
                self.assertIn(row[field], report["scans"])
                self.assertEqual(report["scans"][row[field]]["exit_code"], 0)
        for digest, record in report["scans"].items():
            self.assertEqual(sha(HERE / "scans" / (digest + ".json")), record["public_json_sha256"])
        for row in self.load("provenance-index.json")["files"]:
            relative = row["snapshot"].split("/benchmark/" + HERE.name + "/", 1)[1]
            self.assertEqual(sha(HERE / relative), row["snapshot_sha256"])

    def test_no_implicit_admission(self):
        composition = self.load("composition.json")
        self.assertFalse(composition["execution_enabled"])
        self.assertFalse(composition["rollout_ready"])
        self.assertEqual(composition["host_sha256"], HOST)
        self.assertEqual(len(composition["board_changes"]), 5)
        self.assertEqual(composition["new_native_paths"], [])
        self.assertEqual(self.load("new-native-admission-draft.json")["admissions"], [])
        self.assertFalse(self.load("registry-delta.json")["applied"])

    def test_honest_surface_results(self):
        mac = self.load("gates/mac.json")
        self.assertEqual(mac["actual_os"], "Darwin")
        self.assertFalse(mac["device_access"])
        self.assertEqual(mac["production_gates_passed"], mac["production"]["exit_code"] == 0)
        vm_path = HERE / "gates/vm.json"
        if vm_path.exists():
            vm = self.load("gates/vm.json")
            self.assertEqual(vm["actual_os"], "Linux")
            self.assertEqual(vm["production_gates_passed"], vm["production"]["exit_code"] == 0)
        else:
            attempt = self.load("gates/vm-attempt.json")
            self.assertFalse(attempt["vm_verified"])
            self.assertNotEqual(attempt["command"]["exit_code"], 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["disabled", "evidence"])
    args = parser.parse_args()
    classes = [DisabledTests] if args.part == "disabled" else [EvidenceTests] if args.part == "evidence" else [DisabledTests, EvidenceTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(test_class) for test_class in classes)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
