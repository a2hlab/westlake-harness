import ast
import hashlib
import json
from pathlib import Path
import sys
import unittest

from validation import require_empty_slots, require_single_delta, require_transaction_identity

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class AssemblyTests(unittest.TestCase):
    def test_pins_disabled_and_single_bridge(self):
        composition = load("composition.json")
        self.assertTrue(composition["assembly_base_sha256"].startswith("91272eaf"))
        self.assertTrue(composition["transaction_base_sha256"].startswith("190afedd"))
        self.assertEqual(composition["changed_payload_members"], ["payload/android/lib64/liboh_adapter_bridge.so"])
        for name in ["execution_enabled", "rollout_ready", "device_access"]:
            self.assertIs(composition[name], False)
        for name, field in [("bundle.json", "bundle_sha256"), ("native-manifest.json", "native_manifest_sha256"), ("native-inputs.json", "native_inputs_sha256")]:
            self.assertEqual(hashlib.sha256((HERE / "manifests" / name).read_bytes()).hexdigest(), composition[field])
        self.assertTrue(composition["boot_and_jars_unchanged_from_u13"])
        self.assertTrue(composition["host_sha256"].startswith("2a87118e"))

    def test_single_delta_rejects_second_member(self):
        old = {"bridge": "old", "host": "same"}
        new = {"bridge": "new", "host": "same"}
        self.assertEqual(require_single_delta(old, new, "bridge", "new"), ["bridge"])
        new["host"] = "different"
        with self.assertRaises(ValueError):
            require_single_delta(old, new, "bridge", "new")

    def test_baseline_parameter_accepts_two_identities_rejects_drift(self):
        composition = load("composition.json")
        for field in ["assembly_base_sha256", "transaction_base_sha256"]:
            require_transaction_identity(composition[field], composition[field])
        with self.assertRaises(ValueError):
            require_transaction_identity(composition["assembly_base_sha256"], composition["transaction_base_sha256"])
        with self.assertRaises(ValueError):
            require_transaction_identity("", "")
        with self.assertRaises(ValueError):
            require_transaction_identity("same", "same")

    def test_cli_has_required_transaction_arguments(self):
        tree = ast.parse((HERE / "assemble.py").read_text())
        arguments = {node.args[0].value: node for node in ast.walk(tree) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument" and node.args}
        for name in ["--transaction-base", "--transaction-base-sha256", "--board-baseline"]:
            self.assertTrue(next(row.value.value for row in arguments[name].keywords if row.arg == "required"))
        text = (HERE / "assemble.py").read_text()
        self.assertIn('bundle["static_checks"]["baseline_bundle_sha256"] = args.transaction_base_sha256', text)
        self.assertIn('executor.prepare(output, base / "native")', text)
        self.assertIn('current = base_files[entry["target"]]', text)

    def test_three_empty_slots_and_rejected_unreviewed_member(self):
        slots = load("slots.json")["slots"]
        require_empty_slots(slots)
        with self.assertRaises(ValueError):
            require_empty_slots(slots + [slots[0]])
        changed = [dict(row, applied=row["id"] == "icu-wall-two") for row in slots]
        with self.assertRaises(ValueError):
            require_empty_slots(changed)

    def test_transaction_is_true_current_base_not_assembly_base(self):
        composition = load("composition.json")
        plan = load("transaction-plan.json")
        self.assertEqual(plan["static_baseline_binding"], composition["transaction_base_sha256"])
        self.assertEqual(len(plan["baseline"]), 316)
        self.assertEqual(len(plan["expected"]), 319)
        self.assertEqual(len(plan["additions"]), 3)
        self.assertEqual(len(plan["changes"]), 41)
        bundle = load("manifests/bundle.json")
        self.assertEqual(bundle["image_gate_reference"]["baseline_bundle_sha256"], composition["transaction_base_sha256"])


class StaticTests(unittest.TestCase):
    def test_ordered_needed_and_all_four_new_imports(self):
        imports = load("imports.json")
        self.assertEqual(imports["needed_count"], 35)
        self.assertTrue(imports["needed_unchanged_ordered"])
        self.assertEqual(len(imports["new_undefined"]), 4)
        self.assertEqual(len(imports["inherited_e34_imports"]), 3)
        self.assertEqual(len(imports["patch_new_undefined"]), 1)
        self.assertIn("SetSubWindowZLevel", imports["patch_new_undefined"][0])
        self.assertTrue(imports["provider"]["sha256"].startswith("9551c7fe"))
        self.assertEqual(set(imports["new_undefined"]), {symbol for provider in imports["all_new_import_providers"] for symbol in provider["matched_imports"]})
        self.assertFalse(imports["removed_undefined"])

    def test_raw_adr_diagnostic_not_silently_normalized(self):
        delta = load("open-delta.json")
        self.assertEqual((delta["old_sites"], delta["new_sites"]), (3, 3))
        self.assertFalse(delta["old_namespace_edges"])
        self.assertFalse(delta["candidate_namespace_edges"])
        self.assertEqual(len(delta["delta"]["added"]), 1)
        self.assertEqual(len(delta["delta"]["removed"]), 1)
        self.assertIn("unknown:adr", delta["delta"]["added"][0]["path"][0])
        proof = load("adr-proof.json")
        self.assertEqual({row["literal"] for row in proof["rows"]}, {"libmali.so.0"})
        self.assertEqual({row["flags"] for row in proof["rows"]}, {0x102})
        self.assertEqual({row["namespace"] for row in proof["rows"]}, {"caller-default"})
        self.assertIsNone(load("static-allowance-draft.json")["approved_by"])

    def test_pending_findings_and_no_production_claim(self):
        report = load("report-summary.json")
        self.assertEqual(report["native_baseline"], "PASS")
        self.assertEqual(report["native_candidate"], "REJECT")
        self.assertEqual(report["static_vs_u13"], "REJECT")
        self.assertEqual(report["static_vs_transaction"], "REJECT")
        self.assertEqual((report["auto_identical_count"], report["new_findings_count"]), (159, 39))
        self.assertEqual(report["new_findings_by_gate"], {"N1": 39, "N2": 0})
        pending = load("needs-outer-review.json")
        self.assertEqual(len(pending["new_findings"]), 39)
        self.assertIsNone(pending["approved_by"])
        self.assertFalse(load("registry-delta.json")["applied"])
        for field in ["active_registry_written", "production_run", "device_access", "execution_enabled"]:
            self.assertIs(report[field], False)
        self.assertEqual(report["vm_replay"], "deferred")

    def test_abi_219_consumers_and_only_three_function_diffs(self):
        abi = load("evidence/abi-consumers.json")
        for name in ["removed", "drift", "consumer_breaks"]:
            self.assertFalse(abi[name])
        self.assertEqual(len(abi["added"]), 4)
        self.assertEqual(len(abi["consumers"]), 219)
        self.assertEqual(len(abi["call_diffs"]), 3)
        self.assertFalse([row for row in abi["call_diffs"] if row["removed_callees"]])

    def test_source_snapshot_identity_and_donor_provenance(self):
        provenance = load("provenance.json")
        self.assertEqual(len(provenance["sources"]), 50)
        self.assertTrue(provenance["two_donor_artifacts_same_bytes"])
        self.assertFalse(provenance["local_rebuild"])
        self.assertFalse(provenance["vm_used"])
        for row in provenance["snapshots"] + provenance["build_logs"]:
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        scan = load("manifests/scan-manifest.json")
        for name, row in scan["sources"].items():
            if name.startswith("u14-bridge-"):
                self.assertEqual(hashlib.sha256((HERE / "inputs" / name).read_bytes()).hexdigest(), row["source_sha256"])

    def test_three_admissions_are_preview_not_active(self):
        preview = load("new-native-admissions-draft.json")
        self.assertFalse(preview["applied"])
        self.assertEqual(len(preview["admissions"]), 3)
        for row in preview["admissions"]:
            self.assertIsNone(row["approved_by"])
            self.assertEqual(row["package_manifest_sha256"], load("composition.json")["native_manifest_sha256"])
            self.assertTrue(row["auto_from"]["package_manifest_sha256"].startswith("85aef68e"))


if __name__ == "__main__":
    mode = next((value for value in sys.argv[1:] if value in ["--assembly", "--static"]), None)
    classes = [AssemblyTests] if mode == "--assembly" else [StaticTests] if mode == "--static" else [AssemblyTests, StaticTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(selected) for selected in classes)
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
