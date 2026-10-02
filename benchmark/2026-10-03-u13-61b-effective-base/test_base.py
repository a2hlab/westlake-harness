import hashlib
import json
from pathlib import Path
import unittest

from validation import require_board_local_identity, require_exact_reference_delta

HERE = Path(__file__).resolve().parent
TARGETS = ["/system/lib64/libinstalls.z.so", "/system/lib64/platformsdk/libinstalls.z.so"]
INSTALLS = "51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5"
OLD = "2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0"


def load(name):
    return json.loads((HERE / name).read_text())


def reference(name):
    return {line.split()[1]: line.split()[0] for line in (HERE / "evidence" / name).read_text().splitlines()}


class BaseTests(unittest.TestCase):
    def test_exact_signed_full_identity(self):
        plan = load("transaction-plan.json")
        composition = load("composition.json")
        self.assertEqual(plan["baseline"], composition["baseline"]["expected"])
        self.assertEqual(plan["expected"], composition["candidate"]["expected"])
        self.assertEqual((len(plan["baseline"]), len(plan["expected"])), (316, 319))
        self.assertEqual((len(plan["additions"]), len(plan["changes"])), (3, 40))
        self.assertEqual(plan["static_baseline_binding"], composition["base_bundle_sha256"])

    def test_services_not_actions(self):
        plan = load("transaction-plan.json")
        require_board_local_identity(plan["baseline"], plan["expected"], TARGETS, INSTALLS, {row["target"] for row in plan["changes"]})
        self.assertFalse(set(TARGETS) & set(plan["additions"]))
        self.assertFalse(load("critical-result.json")["service_actions"])

    def test_wrong_expected_or_service_action_rejected(self):
        plan = load("transaction-plan.json")
        changed = dict(plan["expected"], **{TARGETS[0]: OLD})
        with self.assertRaises(ValueError):
            require_board_local_identity(plan["baseline"], changed, TARGETS, INSTALLS, set())
        with self.assertRaises(ValueError):
            require_board_local_identity(plan["baseline"], plan["expected"], TARGETS, INSTALLS, {TARGETS[1]})

    def test_reference_only_two_lines(self):
        old = reference("candidate-runtime-before.txt")
        new = reference("candidate-runtime-after.txt")
        require_exact_reference_delta(old, new, TARGETS, OLD, INSTALLS)
        self.assertEqual((len(old), len(new)), (123, 123))
        changed = dict(new, **{"/system/android/lib64/libart.so": "wrong"})
        with self.assertRaises(ValueError):
            require_exact_reference_delta(old, changed, TARGETS, OLD, INSTALLS)

    def test_manifest_and_inputs_unchanged(self):
        composition = load("composition.json")
        self.assertEqual(hashlib.sha256((HERE / "manifests/native-manifest.json").read_bytes()).hexdigest(), composition["native_manifest_sha256"])
        self.assertTrue(composition["native_manifest_sha256"].startswith("85aef68e"))
        self.assertTrue(composition["native_inputs_sha256"].startswith("c40faa79"))
        self.assertTrue(composition["base_native_manifest_sha256"].startswith("4db32703"))
        self.assertFalse(composition["native_manifest_changed"])
        self.assertFalse(composition["output_bytes_changed"])
        self.assertTrue(composition["original_package_unchanged"])

    def test_only_metadata_changes_and_evidence_copies(self):
        delta = load("file-delta.json")
        candidate = next(row for row in delta["variants"] if row["variant"] == "candidate")
        self.assertEqual({row["path"] for row in candidate["rows"]}, {"bundle.json", "reference/runtime.txt"})
        baseline = next(row for row in delta["variants"] if row["variant"] == "base")
        self.assertEqual({row["path"] for row in baseline["rows"]}, {"bundle.json", "reference/runtime.txt", *["native/board-local" + target for target in TARGETS]})

    def test_static_and_active_native_no_new_binding(self):
        for name in ["static-original", "static-61b"]:
            self.assertEqual(load("evidence/" + name + ".json")["status"], "PASS")
        for name in ["native-base", "native-candidate"]:
            report = load("evidence/" + name + ".json")
            self.assertEqual(report["status"], "PASS")
            self.assertFalse(report["errors"])
            self.assertTrue(all(row["rejected"] == 0 for row in report["gates"].values()))

    def test_source_and_board_scope(self):
        composition = load("composition.json")
        self.assertEqual(composition["source_sha256"], INSTALLS)
        self.assertEqual(len(composition["board_local_members"]), 2)
        self.assertTrue(composition["serial"].startswith("61b06572"))
        manifest = load("manifests/candidate-bundle.json")
        self.assertEqual(manifest["transaction_scope_serial"], composition["serial"])
        self.assertFalse(manifest["rollout_ready"])

    def test_no_historical_production_pass(self):
        report = load("report-summary.json")
        self.assertFalse(report["production_run"])
        self.assertFalse(report["execution_enabled"])
        self.assertFalse(report["device_access"])
        self.assertEqual(report["vm_replay"], "outer pending")
        script = (HERE / "offline_gates.py").read_text()
        self.assertIn('"--baseline-native", BASE / "native"', script)
        self.assertIn('require_board_local_identity(', script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
