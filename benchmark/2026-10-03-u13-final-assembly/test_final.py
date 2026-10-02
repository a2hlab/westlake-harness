import copy
import hashlib
import json
from pathlib import Path
import unittest

from validation import compare_new

HERE = Path(__file__).resolve().parent


def read(name):
    return json.loads((HERE / name).read_text())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class FinalAssemblyTests(unittest.TestCase):
    def test_composition(self):
        composition = read("composition.json")
        self.assertEqual(composition["changed_payload_members"], ["payload/android/framework/oh-adapter-runtime.jar"])
        self.assertEqual(composition["host_sha256"], "2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e")
        self.assertTrue(composition["boot_group_unchanged"])
        self.assertFalse(composition["execution_enabled"])
        for board in composition["candidate_boards"].values():
            self.assertEqual(board["expected"]["/system/android/framework/oh-adapter-runtime.jar"], composition["runtime_jar_sha256"])

    def test_exact_findings_and_new_identity(self):
        report = read("evidence/native-v3.json")
        rows = read("transfer-check.json")["new_finding_mapping"]
        for row in rows:
            self.assertEqual(row["old_finding"], row["new_finding"])
            self.assertNotEqual(row["old_issue_id"], row["new_issue_id"])
            expected = digest(dict(gate="N1", package_manifest_sha256=report["package_manifest_sha256"],
                inputs_sha256=report["inputs_sha256"], finding=row["new_finding"]))
            self.assertEqual(expected, row["new_issue_id"])

    def test_source_line_drift_not_ignored(self):
        report = read("evidence/native-v3.json")
        changed = copy.deepcopy(report)
        finding = next(item for item in changed["gates"]["N1"]["findings"] if item.get("profile") == "u13-m1-compat-shim.cpp")
        finding["detail"]["evidence"]["line"] += 1
        rows = compare_new(report, changed)
        self.assertFalse(all(row["equal"] for row in rows))

    def test_added_finding_not_ignored(self):
        report = read("evidence/native-v3.json")
        changed = copy.deepcopy(report)
        finding = copy.deepcopy(next(item for item in changed["gates"]["N1"]["findings"] if item.get("profile") == "u13-m1-compat-shim.cpp"))
        finding["detail"]["function"] = "unreviewed_function"
        changed["gates"]["N1"]["findings"].append(finding)
        with self.assertRaises(ValueError):
            compare_new(report, changed)

    def test_actual_production_delta_is_preserved(self):
        check = read("transfer-check.json")
        self.assertFalse(check["production_delta_matches_signed"])
        for row in check["compat_aliases"]:
            delta = row["open_site_delta"]
            self.assertEqual(digest(delta), row["delta_sha256"])
            self.assertEqual(delta["namespace_api_changes"], {})
            self.assertEqual(delta["namespace_literal_changes"], {"added": [], "removed": []})
            sites = {name: delta[name] for name in ["added", "removed"]}
            self.assertEqual(digest(sites), check["approved_delta_sha256"])
            self.assertNotEqual(digest(delta), digest(sites))

    def test_unapproved_jar_drop_remains_visible(self):
        jar = next(item for item in read("evidence/static-v3.json")["members"] if item.get("kind") == "DEX-JAR")
        self.assertEqual(jar["status"], "REJECT")
        self.assertIn("DROPPED  Ladapter/core/GcmDefaultNonce$2;", jar["check"]["stdout"])
        self.assertIn("1 dropped, 0 reshaped, 10 added", jar["check"]["stdout"])
        self.assertEqual(jar["deployed_sha256"], "0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f")

    def test_no_approval_or_production_success_fabricated(self):
        check = read("transfer-check.json")
        self.assertFalse(check["approvals_transferred"])
        self.assertTrue(check["registry_unchanged"])
        self.assertTrue(check["exact_new_findings"])
        self.assertTrue(check["strings_equal"])
        self.assertEqual((check["auto_identical"], check["new_findings"]), (157, 2))

    def test_final_approval_rows_and_manifest_bindings(self):
        rows = read("registry-delta.json")["exceptions"]
        self.assertEqual(len(rows), 159)
        self.assertEqual(len({row["issue_id"] for row in rows}), 159)
        composition = read("composition.json")
        self.assertTrue(composition["approvals_transferred"])
        for row in rows:
            self.assertEqual(row["package_manifest_sha256"], composition["native_manifest_sha256"])
            self.assertEqual(row["inputs_sha256"], composition["native_inputs_sha256"])
            self.assertEqual(row["approved_by"], "outer(claude)")
            self.assertTrue(row["approved_at"])
        for name, field in [("native-manifest.json", "native_manifest_sha256"), ("native-inputs.json", "native_inputs_sha256"), ("bundle.json", "bundle_sha256")]:
            self.assertEqual(hashlib.sha256((HERE / "manifests" / name).read_bytes()).hexdigest(), composition[field])
        manifest = read("manifests/native-manifest.json")
        bundle = read("manifests/bundle.json")
        self.assertEqual(manifest["files"]["payload/android/framework/oh-adapter-runtime.jar"], bundle["runtime_jar"]["sha256"])
        self.assertFalse(bundle["rollout_ready"])
        self.assertNotIn("window_authorization", bundle)

    def test_final_static_approval_is_narrow(self):
        policy = read("static-policy.json")
        self.assertEqual(len(policy["native"]), 2)
        self.assertEqual(len(policy["jars"]), 1)
        jar = next(iter(policy["jars"].values()))
        self.assertEqual(jar["allow_drop"], ["Ladapter/core/GcmDefaultNonce$2;"])
        self.assertEqual(len(jar["allow_add"]), 10)
        self.assertTrue(all(item.endswith(";") for item in jar["allow_add"]))
        self.assertEqual(read("evidence/static-v3-approved.json")["status"], "PASS")
        native = read("evidence/native-v3-approved.json")
        self.assertEqual(native["status"], "PASS")
        self.assertEqual(sum(gate["excepted"] for gate in native["gates"].values()), 159)

    def test_actual_production_receipts_remain_unarmed(self):
        composition = read("composition.json")
        receipt = read("production-receipts.json")
        self.assertTrue(receipt["production_gates_passed"])
        self.assertEqual({row["surface"] for row in receipt["receipts"]}, {"mac", "vm"})
        for surface, expected_os in [("mac", "Darwin"), ("vm", "Linux")]:
            gates = read("gates/" + surface + ".json")
            self.assertEqual(gates["actual_os"], expected_os)
            self.assertEqual(gates["bundle_sha256"], composition["bundle_sha256"])
            self.assertTrue(gates["production_gates_passed"])
            self.assertEqual(gates["production"]["exit_code"], 0)
            self.assertEqual(gates["composed_frozen_violations"], 0)
            self.assertTrue(all(row["exit_code"] == 0 for row in gates["records"]))
            plan = read("evidence/" + surface + "-executor-plan.json")
            self.assertEqual(plan["bundle_sha256"], composition["bundle_sha256"])
            self.assertTrue(plan["gates_passed"])
            self.assertFalse(plan["device_io"])
            self.assertFalse(plan["deployable"])
            self.assertTrue(plan["image_gates"]["G1"] and plan["image_gates"]["G2"])
            self.assertEqual(plan["static_checks"]["status"], "PASS")
            self.assertEqual(plan["native_tickets"][0]["report"]["inputs_sha256"], composition["native_inputs_sha256"])
        results = read("results.json")
        self.assertTrue(results["production_gates_passed"])
        self.assertFalse(results["stage_a_authorized"])
        self.assertFalse(results["execution_enabled"])


if __name__ == "__main__":
    unittest.main()
