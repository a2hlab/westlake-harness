import copy
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validation import ADDED, DEX2OAT, DRIVER, IMAGE_NAMES, check_plan, check_receipt

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class InputTests(unittest.TestCase):
    def test_effective_nine_and_one_swap(self):
        check_plan(load("plan.json"), load("expected-images.json"), load("native-slots.json"))
        self.assertEqual(load("plan.json")["changed_bcp"], ["adapter-mainline-stubs.jar"])

    def test_no_inferred_transaction_promotion(self):
        plan = load("plan.json")
        plan["transaction_base"]["common"] = plan["content_bases"]["common"]
        with self.assertRaisesRegex(ValueError, "inferred"):
            check_plan(plan, load("expected-images.json"), load("native-slots.json"))

    def test_wrong_input_and_runtime_in_bcp(self):
        for change in ["wrong-stubs", "runtime-in-bcp"]:
            plan = load("plan.json")
            if change == "wrong-stubs":
                plan["bcp"][6]["sha256"] = "f" * 64
            else:
                plan["runtime_jar"]["in_bcp"] = True
            with self.assertRaises(ValueError):
                check_plan(plan, load("expected-images.json"), load("native-slots.json"))

    def test_pending_native_and_exclusions(self):
        slots = load("native-slots.json")
        slots["slots"][0]["applied"] = True
        with self.assertRaisesRegex(ValueError, "arrival"):
            check_plan(load("plan.json"), load("expected-images.json"), slots)
        slots["slots"] = []
        with self.assertRaisesRegex(ValueError, "Both pending"):
            check_plan(load("plan.json"), load("expected-images.json"), slots)

    def test_exact_adds_remain_unsigned(self):
        approval = load("allow-add.pending.json")
        self.assertEqual(approval["descriptors"], ADDED)
        self.assertFalse(approval["approved"])
        self.assertFalse(approval["execution_enabled"])

    def test_cold_source_snapshots(self):
        for row in load("source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        receipt = load("donor-receipt-status.json")
        self.assertEqual(receipt["receipt_matches_current_artifact"], receipt["artifact_sha256"] == receipt["receipt_output_sha256"])
        self.assertFalse(receipt["blocks_final_provenance_claim"])
        self.assertEqual(receipt["classes_dex_sha256"], receipt["receipt_classes_dex_sha256"])


class NativeTests(unittest.TestCase):
    def test_exact_runtime_only_metadata_and_sources(self):
        binding = load("native-slot-binding.json")
        old, new = load("inputs/native-metadata/baseline-manifest.json"), load("inputs/native-metadata/candidate-manifest.json")
        changes = {name: dict(old=old["files"].get(name), new=digest) for name, digest in new["files"].items() if old["files"].get(name) != digest}
        self.assertEqual(changes, binding["changes"])
        self.assertEqual(len(changes), 1)
        self.assertEqual(set(old["files"]), set(new["files"]))
        self.assertFalse(binding["execution_enabled"])
        self.assertFalse(binding["rollout_ready"])
        self.assertTrue(binding["namespace_manifest_unchanged"])
        for row in load("native-source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        scan = load("inputs/native-metadata/scan-manifest.json")
        self.assertIn("u16-m1-copy.cpp", scan["sources"])

    def test_raw_static_results_are_not_native_admission(self):
        report = load("native-gate-runs.json")
        self.assertEqual(report["consumer_count"], 219)
        self.assertEqual(report["active_registry_sha256"], report["active_registry_sha256_after"])
        self.assertFalse(report["active_registry_updated"])
        self.assertFalse(report["native_production_approved"])
        self.assertEqual(report["abi_summary"], dict(removed=0, added=1, drift=0, consumer_breaks=0, call_diffs=3))
        self.assertEqual(report["open_counts"], {"u15": 197, "u16-t4": 197})
        self.assertTrue(report["needed_unchanged"])
        for variants in report["native_reports"].values():
            for row in variants.values():
                self.assertEqual(row["errors"], [])
                self.assertEqual(row["exit_code"], 1)
                self.assertEqual(row["status"], "REJECT")
        for row in report["records"]:
            self.assertEqual(hashlib.sha256((HERE / row["evidence"]).read_bytes()).hexdigest(), row["evidence_sha256"])

    def test_flutter_and_images_still_pending(self):
        slots = load("inputs/history-t4/native-slots.json")
        self.assertEqual(slots["slots"][0]["state"], "arrived-staged")
        self.assertEqual(slots["slots"][1]["state"], "pending")
        self.assertIsNone(slots["slots"][1]["sha256"])
        self.assertFalse(any(row["applied"] for row in slots["slots"]))
        self.assertTrue(all(row["candidate_sha256"] is None for row in load("expected-images.json")))

    def test_withdrawn_flutter_cannot_replace_u15(self):
        report = load("flutter-withdrawal.json")
        self.assertEqual(report["removed"], ["ATrace_beginSection", "ATrace_endSection", "ATrace_isEnabled"])
        self.assertEqual(report["command_exit_code"], 0)
        self.assertFalse(report["selected"])
        self.assertFalse(report["staged"])
        old, new = load("inputs/native-metadata/baseline-manifest.json"), load("inputs/native-metadata/candidate-manifest.json")
        member = "payload/android/lib64/westlake_flutter/libandroid.so"
        self.assertEqual(new["files"][member], old["files"][member])
        self.assertEqual(new["files"][member], report["baseline_sha256"])
        for path, digest in [(report["evidence"], report["evidence_sha256"]), (report["report"], report["report_sha256"])]:
            self.assertEqual(hashlib.sha256((HERE / path).read_bytes()).hexdigest(), digest)

    def test_review_preserves_all_three_calls_and_two_line_shifts(self):
        report = load("native-review.pending.json")
        self.assertFalse(report["approved"])
        self.assertEqual(report["abi_call_diffs"], load("evidence/u16-abi-runtime.json")["call_diffs"])
        self.assertEqual(len(report["abi_call_diffs"]), 3)
        self.assertEqual(report["equal_findings"], 202)
        self.assertEqual(len(report["n1_line_shifts"]), 2)
        for row in report["n1_line_shifts"]:
            before = copy.deepcopy(row["before"])
            before["detail"]["evidence"]["line"] = row["after"]["detail"]["evidence"]["line"]
            self.assertEqual(before, row["after"])
            self.assertIsNone(row["approved_by"])
            for label in ["old", "new"]:
                self.assertEqual(hashlib.sha256((HERE / row[label + "_snapshot"]).read_bytes()).hexdigest(), row[label + "_snapshot_sha256"])


class PairTests(unittest.TestCase):
    def test_exact_observer_keys_and_missing_flutter_watch_refuses(self):
        receipt = load("fix-observer-receipt.json")
        self.assertEqual(receipt["keys_sha256"], "6f42bf0a5265da6709c63698adb5f97c7bffd1e18e9fa70c37dae64c00239d38")
        self.assertEqual((receipt["artifacts"], receipt["gaps"], receipt["images_pending"]), (8, 0, 27))
        self.assertFalse(receipt["full_bundle_coverage_claimed"] or receipt["execution_enabled"])
        self.assertEqual(hashlib.sha256((HERE / "increments.csv").read_bytes()).hexdigest(), receipt["increments_sha256"])
        keys = load("inputs/observers/u16-stage-a-keys.json")
        self.assertEqual(hashlib.sha256((HERE / "inputs/observers/u16-stage-a-keys.json").read_bytes()).hexdigest(), receipt["keys_sha256"])
        tool = HERE / "inputs/observers/check_fix_observers.py.txt"
        self.assertEqual(hashlib.sha256(tool.read_bytes()).hexdigest(), receipt["checker_sha256"])
        with (HERE / "increments.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["candidate_sha256"] for row in rows if row["target"].endswith("westlake_flutter/libandroid.so")},
            {"eb90a6409c9caaba058d2463cad9c193d344527051455d8aca8421e6b7011b4f"})
        command = [sys.executable, str(tool), str(HERE / "increments.csv")]
        positive = subprocess.run([*command, str(HERE / "inputs/observers/u16-stage-a-keys.json")], capture_output=True, text=True)
        self.assertEqual(positive.returncode, 0, positive.stdout + positive.stderr)
        for board in keys["boards"]:
            for shard in board["shards"]:
                for item in (shard.get("per_key") or {}).values():
                    if isinstance(item, dict) and "eb90a640" in item.get("source", ""):
                        item["source"] = "fixture with Flutter observers removed"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "keys.json"
            changed.write_text(json.dumps(keys))
            negative = subprocess.run([*command, str(changed)], capture_output=True, text=True)
        self.assertEqual(negative.returncode, 1, negative.stdout + negative.stderr)
        self.assertIn("8 artifacts, 2 without an observer", negative.stdout)

    def test_exact_two_objects_and_native_domain_preserved(self):
        binding = load("native-pair-binding.json")
        old, new = load("inputs/native-pair-metadata/baseline-manifest.json"), load("inputs/native-pair-metadata/candidate-manifest.json")
        changes = {name: dict(old=old["files"].get(name), new=digest) for name, digest in new["files"].items() if old["files"].get(name) != digest}
        self.assertEqual(changes, binding["changes"])
        self.assertEqual(set(changes), {"payload/android/lib64/liboh_android_runtime.so", "payload/android/lib64/westlake_flutter/libandroid.so"})
        self.assertEqual(set(old["files"]), set(new["files"]))
        self.assertEqual(old["files"]["payload/android/lib64/westlake_native/libandroid.so"], new["files"]["payload/android/lib64/westlake_native/libandroid.so"])
        self.assertFalse(binding["execution_enabled"])
        self.assertFalse(binding["rollout_ready"])
        self.assertIsNone(binding["final_bundle_sha256"])
        for row in load("flutter-source-snapshots.json"):
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["snapshot_sha256"])
        self.assertIn("u16-flutter-impeller.cpp", load("inputs/native-pair-metadata/scan-manifest.json")["sources"])

    def test_corrected_flutter_abi_and_raw_gate_hashes(self):
        report = load("native-pair-gates.json")
        flutter = load("evidence/u16-a3-flutter-abi.json")
        self.assertEqual(flutter["removed"], [])
        self.assertEqual(flutter["added"], ["eglGetProcAddress"])
        self.assertEqual(report["members"]["flutter"]["abi_summary"], dict(removed=0, added=1, drift=0, consumer_breaks=0, call_diffs=0))
        self.assertEqual(report["members"]["runtime"]["abi_summary"], dict(removed=0, added=1, drift=0, consumer_breaks=0, call_diffs=3))
        self.assertEqual(report["consumer_count"], 219)
        self.assertEqual(report["active_registry_sha256"], report["active_registry_sha256_after"])
        self.assertFalse(report["active_registry_updated"])
        self.assertFalse(report["native_production_approved"])
        for row in report["records"]:
            self.assertEqual(hashlib.sha256((HERE / row["evidence"]).read_bytes()).hexdigest(), row["evidence_sha256"])
        for member in report["members"].values():
            self.assertTrue(member["needed_unchanged"])
        for variants in report["native_reports"].values():
            for row in variants.values():
                self.assertEqual(row["errors"], [])
                self.assertEqual(row["status"], "REJECT")
                self.assertEqual(row["exit_code"], 1)

    def test_withdrawn_identity_rejected_and_all_finalization_disabled(self):
        slots = load("native-slots.json")
        self.assertEqual([row["state"] for row in slots["slots"]], ["arrived-staged", "arrived-staged"])
        self.assertFalse(any(row["applied"] for row in slots["slots"]))
        slots["slots"][1]["sha256"] = load("flutter-withdrawal.json")["artifact_sha256"]
        with self.assertRaisesRegex(ValueError, "corrected"):
            check_plan(load("plan.json"), load("expected-images.json"), slots)
        composition = load("composition.json")
        for name in ["execution_enabled", "rollout_ready"]:
            self.assertFalse(composition[name])
        for name in ["final_bundle_sha256", "final_manifest_sha256", "final_inputs_sha256"]:
            self.assertIsNone(composition[name])
        self.assertEqual(composition["transaction_base"], {"common": None, "61b": None})


class OuterPacketTests(unittest.TestCase):
    def test_complete_unsigned_evidence_bound_packet(self):
        from build_approval_packet import validate_packet
        packet = load("outer-approval-packet.json")
        self.assertTrue(validate_packet(HERE, packet))
        self.assertEqual(packet["counts"], {"flutter-open": 4, "runtime-line-shift": 2,
            "runtime-call-set": 3, "strings": 8, "manual_rows": 17})
        self.assertTrue(all(row["recommendation"]["label"] == "批" for row in packet["decisions"]))
        runs = load("outer-packet-runs.json")
        self.assertEqual(len(runs["records"]), 13)
        self.assertTrue(all(row["exit_code"] == 0 for row in runs["records"]))
        self.assertEqual(runs["active_registry_before"], runs["active_registry_after"])
        self.assertEqual(runs["packet_sha256"], hashlib.sha256((HERE / "outer-approval-packet.json").read_bytes()).hexdigest())

    def test_evidence_flags_binding_and_excerpt_tampering_rejected(self):
        from build_approval_packet import validate_packet
        for change in ["evidence", "flags", "target", "binding", "artifact", "excerpt"]:
            packet = load("outer-approval-packet.json")
            row = packet["decisions"][0]
            if change == "evidence":
                row["basis"][0]["sha256"] = "f" * 64
            elif change == "flags":
                row["open_site"]["flags"] = ["0x2=NOW"]
            elif change == "target":
                row["open_site"]["path"] = ["libwrong.so"]
            elif change == "binding":
                packet["native_inputs_sha256"] = "f" * 64
            elif change == "artifact":
                next(iter(packet["selected_artifacts"].values()))["new"] = "f" * 64
            else:
                row["disassembly"][0]["excerpt"][0] = "invented instruction"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                validate_packet(HERE, packet)

    def test_invented_authority_or_execution_rejected(self):
        from build_approval_packet import validate_packet
        for field in ["signer", "signed_at", "execution_enabled", "rollout_ready", "gate_registry_applied",
            "final_bundle_sha256", "decision", "approved_by"]:
            packet = load("outer-approval-packet.json")
            if field in ["decision", "approved_by"]:
                packet["decisions"][0][field] = "invented approval"
            else:
                packet[field] = True
            with self.subTest(field=field), self.assertRaises(AssertionError):
                validate_packet(HERE, packet)


class BakeTests(unittest.TestCase):
    def test_disabled_before_probe(self):
        result = subprocess.run(["bash", str(HERE / "planned-bake.sh")], capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent"})
        self.assertEqual(result.returncode, 78)
        self.assertIn("DISABLED", result.stdout)

    def test_exact_recipe_delta_and_machine(self):
        for name in ["planned-bake.sh", "dex2oat-tee.sh"]:
            subprocess.run(["bash", "-n", str(HERE / name)], check=True)
            old = (HERE / "inputs/source/u15-recipe" / (name + ".txt")).read_text()
            expected = old.replace("U15", "U16").replace("u15", "u16").replace("bitmap-nsd-9e55-94a9-v1", "stubs-8593-runtime-f6f5-v1")
            self.assertEqual((HERE / name).read_text(), expected)
        script = (HERE / "planned-bake.sh").read_text()
        for marker in ["ecs-9f6c", "HW248_HOME", "session_tee_exit_code", "hostlibs-run1", DEX2OAT, DRIVER]:
            self.assertIn(marker, script)

    def test_identical_planned_argv_not_actual(self):
        argv = load("planned-argv.json")
        self.assertEqual(argv["run1"], argv["run2"])
        self.assertIsNone(argv["actual_argv_sha256"])
        self.assertEqual(sum(arg.startswith("--dex-file=") for arg in argv["run1"]), 9)
        self.assertFalse(any("oh-adapter-runtime.jar" in arg for arg in argv["run1"]))

    def test_complete_unexecuted_pair(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        pair = load("paired-receipt.template.json")
        self.assertIsNone(pair["selected_run"])
        self.assertEqual([row["run"] for row in pair["runs"]], [1, 2])
        for row in pair["runs"]:
            self.assertEqual(row["input_jars"], inputs)
            self.assertEqual(set(row["outputs"]), IMAGE_NAMES)
            self.assertTrue(all(value is None for value in row["outputs"].values()))
            with self.assertRaises(ValueError):
                check_receipt(row, inputs, row["outputs"])

    def test_incomplete_images_and_fake_hash(self):
        images = load("expected-images.json")
        with self.assertRaisesRegex(ValueError, "27 distinct"):
            check_plan(load("plan.json"), images[:-1], load("native-slots.json"))
        images[0]["candidate_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "unknown"):
            check_plan(load("plan.json"), images, load("native-slots.json"))

    def test_failed_logging_and_old_approval(self):
        inputs = {row["name"]: row["sha256"] for row in load("plan.json")["bcp"]}
        outputs = {name: "a" * 64 for name in IMAGE_NAMES}
        receipt = dict(status="verified", input_jars=inputs, outputs=outputs, actual_argv=["synthetic-not-a-bake"],
            dex2oat_sha256=DEX2OAT, driver_sha256=DRIVER, frozen_driver_exit_code=6, dex2oat_exit_code=0, tee_exit_code=0,
            session_tee_exit_code=0, script_exit_code=0, exception_used=False,
            **{name: "a" * 64 for name in ["argv_sha256", "toolchain_identity_sha256", "hostlibs_sha256", "build_log_sha256", "session_log_sha256"]})
        check_receipt(receipt, inputs, outputs)
        for field in ["dex2oat_exit_code", "tee_exit_code", "session_tee_exit_code", "script_exit_code"]:
            broken = copy.deepcopy(receipt)
            broken[field] = 1
            with self.assertRaisesRegex(ValueError, "failed"):
                check_receipt(broken, inputs, outputs)
        receipt["exception_used"] = True
        receipt["u15_outer_exception_approval"] = {"approved_by": "outer(claude)"}
        with self.assertRaisesRegex(ValueError, "Historical"):
            check_receipt(receipt, inputs, outputs)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    cases = [InputTests] if mode == "--inputs" else [BakeTests] if mode == "--bake" else [NativeTests] if mode == "--native" else [PairTests] if mode == "--native-pair" else [OuterPacketTests] if mode == "--outer-packet" else [InputTests, BakeTests, NativeTests, PairTests, OuterPacketTests]
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(case) for case in cases)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        execution_enabled=False, rollout_ready=False, board_access=False, vm_access=False, bake_executed=False)))
    sys.exit(0 if result.wasSuccessful() else 1)
