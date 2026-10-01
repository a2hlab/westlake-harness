import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("u11_builder", HERE / "build_window_shim.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class BehaviorFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="u11-window-")
        root = Path(cls.temporary.name)
        workspaces = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
        donor = workspaces / "westlake-harness" / BUILDER.SOURCE_PATH
        if not donor.is_file():
            donor = HERE.parents[1] / BUILDER.SOURCE_PATH
        generated, cls.provenance = BUILDER.donor_source(donor)
        source = root / "window.c"
        source.write_text(generated)
        cls.binary = root / "owner-tests"
        subprocess.run(["/usr/bin/cc", "-std=gnu11", "-O0", "-pthread", "-include", str(source),
                        str(HERE / "window-lock/test_owner.c"), "-o", str(cls.binary)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def replay(self, modes):
        for mode in modes:
            with self.subTest(mode=mode):
                subprocess.run([str(self.binary), str(mode)], check=True, capture_output=True, timeout=10)


class PixelTests(BehaviorFixture):
    def test_rgba_layout_and_full_dirty(self):
        self.replay([0])

    def test_donor_identity_and_cpu_usage(self):
        self.assertEqual(self.provenance["donor_sha256"], BUILDER.SOURCE_SHA)
        self.assertIn("SET_USAGE opcode5 CPU usage3 before dequeue", self.provenance["adaptations"])


class OwnershipTests(BehaviorFixture):
    def test_owner_usage_request_and_handle_failures(self):
        self.replay([1, 2, 3, 7])

    def test_fence_success_failure_and_fenceless_fallback(self):
        self.replay([4, 5, 6])

    def test_post_failure_and_concurrent_windows(self):
        self.replay([8, 9, 10])


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((HERE / "evidence/consumers.json").read_text())
        cls.receipt = json.loads((HERE / "evidence/build-receipt.json").read_text())

    def test_candidate_and_dependency_identity(self):
        self.assertEqual(self.report["candidate_sha256"], self.receipt["candidate_sha256"])
        self.assertEqual(self.report["runtime_sha256"], BUILDER.RUNTIME_SHA)
        self.assertEqual(self.report["candidate_export_count"], 2)
        self.assertEqual(self.report["candidate_dynamic"], {
            "needed": ["liboh_android_runtime.so", "libsurface.z.so", "libc.so"], "soname": ["libandroid.so"]})
        self.assertFalse(self.receipt["board_touched"])

    def test_complete_consumers_and_input_bindings(self):
        self.assertEqual(self.report["scanned_APK_keys"], 166)
        self.assertEqual(self.report["scanned_native_members"], 606)
        self.assertEqual(self.report["lock_consumer_keys"], 21)
        self.assertEqual(self.report["lock_consumer_members"], 26)
        self.assertEqual(self.report["needed_libandroid_keys"], 37)
        self.assertEqual(self.report["needed_libandroid_members"], 171)
        self.assertTrue(all(row["inventory_base_sha_matches"] for row in self.report["input_inventory_bindings"]))
        self.assertEqual(self.report["union_owner_consumer_breaks"], [])
        self.assertEqual(self.report["missing_inline_consumers_all_APK_members"], [])

    def test_unfiltered_abi_and_unapproved_export(self):
        self.assertEqual(self.report["missing_superset_exports"], ["_ZN7_JNIEnv16CallObjectMethodEP8_jobjectP10_jmethodIDz"])
        self.assertIn("pending", self.report["missing_export_approval"])
        reports = {row["file"]: row for row in self.report["canonical_abi_reports"]}
        self.assertEqual(reports["old-root-to-runtime-abi.json"]["consumer_breaks"], 0)
        self.assertEqual(reports["old-root-to-runtime-abi.json"]["call_differences"], 15)
        self.assertEqual(reports["old-root-to-shim-abi.json"]["exit"], 1)
        self.assertEqual(reports["old-root-to-shim-abi.json"]["consumer_breaks"], 816)
        self.assertIn("not measured", self.report["single_owner_maps"])

    def test_outer_conditional_payload_exception(self):
        from window_gate import check
        gate = check()
        self.assertTrue(gate["passed"], gate["errors"])
        self.assertFalse(gate["deploy_authorized"])
        self.assertIn("pending", gate["release_gate"])


if __name__ == "__main__":
    unittest.main()
