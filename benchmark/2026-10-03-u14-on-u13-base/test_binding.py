import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest

from binding import INSTALLERS, check_artifacts, check_base, check_plan

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class BindingTests(unittest.TestCase):
    def test_matching_bases_and_arming_metadata_only(self):
        identities = {"common": dict(signed_unarmed_bundle_sha256="a" * 64, actual_armed_bundle_sha256="b" * 64)}
        data = dict(rollout_ready=False, rollout_blocker="disabled", native={"sha": "same"})
        check_base("common", "a" * 64, "a" * 64, data, data, identities)
        armed = dict(data, rollout_ready=True, rollout_blocker="")
        check_base("common", "b" * 64, "b" * 64, armed, data, identities)
        armed["native"] = {"sha": "changed"}
        with self.assertRaises(ValueError):
            check_base("common", "b" * 64, "b" * 64, armed, data, identities)
        for variant, digest in [("61b", "a" * 64), ("common", "c" * 64)]:
            with self.assertRaises(ValueError):
                check_base(variant, digest, digest, data, data, identities)
        with self.assertRaises(ValueError):
            check_base("common", "a" * 64, "b" * 64, data, data, identities)

    def test_installer_actions_and_candidate_artifact_changes_rejected(self):
        expected = {target: "installer" for target in INSTALLERS}
        plan = dict(baseline=expected.copy(), expected=expected.copy(), changes=[], additions=[], rollout_ready=False)
        check_plan(plan, expected)
        for field in ["baseline", "expected", "changes", "additions", "rollout_ready"]:
            changed = copy.deepcopy(plan)
            if field in ["baseline", "expected"]:
                changed[field][INSTALLERS[0]] = "wrong"
            elif field in ["changes", "additions"]:
                changed[field] = [dict(target=INSTALLERS[0])]
            else:
                changed[field] = True
            with self.assertRaises(ValueError):
                check_plan(changed, expected)
        check_artifacts({"native": "same"}, {"native": "same"})
        with self.assertRaises(ValueError):
            check_artifacts({"native": "same"}, {"native": "other"})

    def test_real_variants_keep_signed_identity_and_no_installer_action(self):
        pins = load("base-identities.json")["variants"]
        for variant in ["common", "61b"]:
            data = load(variant + "/composition.json")
            self.assertIn(data["transaction_base_sha256"], [pins[variant]["signed_unarmed_bundle_sha256"], pins[variant]["actual_armed_bundle_sha256"]])
            check_plan(load(variant + "/transaction-plan.json"), data["complete_u13_identity"]["expected"])
            stable = load(variant + "/artifact-stability.json")
            check_artifacts(stable["previous"], stable["current"])
            self.assertTrue(data["candidate_artifacts_unchanged"])
            self.assertEqual(data["increment_counts"], {"native": 7, "JAR": 2, "image": 19})
            self.assertFalse(data["execution_enabled"])
            self.assertFalse(data["promotion_confirmed"])
        self.assertNotEqual(load("common/composition.json")["installers"], load("61b/composition.json")["installers"])


class ReplayTests(unittest.TestCase):
    def test_external_replay_defaults_disabled_before_any_probe(self):
        environment = dict(os.environ)
        environment.pop("U14_U13_PRODUCTION_REPLAY", None)
        result = subprocess.run(["bash", str(HERE / "replay-production.sh")], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 78)
        self.assertIn("DISABLED", result.stdout)

    def test_fresh_commands_have_matching_baseline_and_preserved_evidence(self):
        report = load("gate-runs.json")
        for row in report["records"]:
            evidence = HERE / "evidence" / Path(row["evidence"]).name
            self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), row["evidence_sha256"])
        for variant in ["common", "61b"]:
            command = next(row["command"] for row in report["records"] if row["evidence"].endswith("/executor-" + variant + ".txt"))
            baseline = command[command.index("--baseline-native") + 1]
            self.assertEqual(baseline, load(variant + "/composition.json")["transaction_base"] + "/native")
            self.assertIn("--dry-run", command)
            self.assertNotIn("--apply", command)
            self.assertEqual(load(variant + "/evidence/static.json")["status"], "PASS")
            for label in ["candidate", "baseline"]:
                native = load(variant + "/evidence/native-" + label + ".json")
                self.assertEqual(native["status"], "PASS")
                self.assertEqual(native["errors"], [])

    def test_missing_g2_is_rejected_not_promoted(self):
        report = load("gate-runs.json")
        for variant in ["common", "61b"]:
            image = load(variant + "/evidence/image-gates.json")
            self.assertTrue(image["G1"])
            executor = load(variant + "/evidence/executor.json")
            if not image["G2"]:
                self.assertEqual(executor["status"], "rejected")
                self.assertIn("G2: FAIL", executor["error"])
            self.assertFalse(executor["device_io"])
        for name in ["device_access", "lock_taken", "production_gates_passed", "promotion_confirmed", "execution_enabled", "vm_used", "remote_oatdump"]:
            self.assertFalse(report[name])
        identity = load("tool-identity.json")
        self.assertEqual(identity["before"], identity["after"])
        self.assertFalse(identity["active_tables_written"])


if __name__ == "__main__":
    selected = [BindingTests] if "--binding" in sys.argv else [ReplayTests] if "--replay" in sys.argv else [BindingTests, ReplayTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(test) for test in selected)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
