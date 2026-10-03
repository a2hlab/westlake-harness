import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

from binding import INSTALLERS, check_artifacts, check_base, check_plan

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class BindingTests(unittest.TestCase):
    def test_explicit_matching_and_future_arming_only(self):
        pins = {"common": dict(candidate_bundle_sha256="a" * 64)}
        candidate = dict(rollout_ready=False, rollout_blocker="disabled", native=dict(sha="same"))
        check_base("common", "a" * 64, "a" * 64, candidate, candidate, pins)
        armed = dict(candidate, rollout_ready=True, rollout_blocker="")
        check_base("common", "b" * 64, "b" * 64, armed, candidate, pins)
        for variant, expected, actual, data in [("61b", "a" * 64, "a" * 64, candidate),
            ("common", "a" * 64, "b" * 64, armed), ("common", "b" * 64, "b" * 64, candidate),
            ("common", "b" * 64, "b" * 64, dict(armed, native=dict(sha="changed")))]:
            with self.assertRaises(ValueError):
                check_base(variant, expected, actual, data, candidate, pins)

    def test_installer_and_payload_changes_refuse(self):
        expected = {target: "same" for target in INSTALLERS}
        plan = dict(baseline=expected.copy(), expected=expected.copy(), changes=[], additions=[], rollout_ready=False)
        check_plan(plan, expected)
        for field in ["baseline", "expected", "changes", "additions", "rollout_ready"]:
            changed = copy.deepcopy(plan)
            if field in ["baseline", "expected"]:
                changed[field][INSTALLERS[0]] = "different"
            elif field in ["changes", "additions"]:
                changed[field] = [dict(target=INSTALLERS[0])]
            else:
                changed[field] = True
            with self.assertRaises(ValueError):
                check_plan(changed, expected)
        check_artifacts({"native": "same"}, {"native": "same"})
        with self.assertRaises(ValueError):
            check_artifacts({"native": "same"}, {"native": "different"})

    def test_real_variants_keep_five_three_twenty_and_local_installers(self):
        pins = load("base-identities.json")["variants"]
        for variant in ["common", "61b"]:
            composition = load(variant + "/composition.json")
            self.assertEqual(composition["transaction_base_sha256"], pins[variant]["candidate_bundle_sha256"])
            check_plan(load(variant + "/transaction-plan.json"), composition["complete_u14_identity"]["expected"])
            stable = load(variant + "/artifact-stability.json")
            check_artifacts(stable["previous"], stable["current"])
            self.assertEqual(composition["increment_counts"], dict(native=5, JAR=3, image=20))
            self.assertFalse(composition["execution_enabled"])
            self.assertFalse(composition["promotion_confirmed"])
        self.assertNotEqual(load("common/composition.json")["installers"], load("61b/composition.json")["installers"])


class ReplayTests(unittest.TestCase):
    def test_fresh_executor_commands_and_evidence_hashes(self):
        runs = load("gate-runs.json")
        for row in runs["records"]:
            evidence = HERE / "evidence" / Path(row["evidence"]).name
            self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), row["evidence_sha256"])
        for variant in ["common", "61b"]:
            row = next(row for row in runs["records"] if row["evidence"].endswith("/executor-" + variant + ".txt"))
            command = row["command"]
            self.assertIn("--dry-run", command)
            self.assertNotIn("--apply", command)
            self.assertEqual(command[command.index("--baseline-native") + 1], load(variant + "/composition.json")["transaction_base"] + "/native")

    def test_pending_refusals_not_approved_or_promoted(self):
        runs = load("gate-runs.json")
        for variant in ["common", "61b"]:
            self.assertEqual(load(variant + "/evidence/executor.json")["status"], "rejected")
            image = load(variant + "/evidence/image-gates.json")
            self.assertTrue(image["G1"])
            self.assertFalse(image["G2"])
            self.assertEqual(load(variant + "/evidence/native-baseline.json")["status"], "PASS")
            native = load(variant + "/evidence/native-candidate.json")
            self.assertEqual(native["status"], "REJECT")
            self.assertEqual(native["errors"], [])
            self.assertEqual({name: gate["rejected"] for name, gate in native["gates"].items()}, dict(N1=99, N2=105))
            static = load(variant + "/evidence/static.json")
            self.assertEqual(static["status"], "REJECT")
            self.assertEqual([row["target"] for row in static["members"] if row["status"] != "PASS"],
                ["/system/android/framework/adapter-mainline-stubs.jar", "/system/android/framework/oh-adapter-runtime.jar"])
        for name in ["device_access", "lock_taken", "production_gates_passed", "promotion_confirmed", "execution_enabled", "vm_used", "remote_oatdump"]:
            self.assertFalse(runs[name])
        identity = load("tool-identity.json")
        self.assertEqual(identity["before"], identity["after"])
        self.assertFalse(identity["active_tables_written"])

    def test_fresh_native_consumers_and_empty_open_delta(self):
        native = load("native-delta-gates.json")
        self.assertEqual(native["consumer_count"], 219)
        self.assertEqual(len(native["members"]), 4)
        self.assertEqual(native["before"], native["after"])
        for row in native["members"]:
            for field in ["removed", "drift", "consumer_breaks"]:
                self.assertEqual(row["abi_summary"][field], 0)
        for variant in ["common", "61b"]:
            for member in load(variant + "/evidence/static.json")["members"]:
                if member["kind"] == "ELF":
                    delta = member["open_site_delta"]
                    self.assertEqual(delta["added"], [])
                    self.assertEqual(delta["removed"], [])
                    self.assertEqual(delta["namespace_api_changes"], {})
                    self.assertEqual(delta["namespace_literal_changes"], dict(added=[], removed=[]))


if __name__ == "__main__":
    selected = [BindingTests] if "--binding" in sys.argv else [ReplayTests] if "--replay" in sys.argv else [BindingTests, ReplayTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(test) for test in selected)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
