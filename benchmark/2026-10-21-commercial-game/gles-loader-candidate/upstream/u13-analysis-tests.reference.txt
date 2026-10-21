import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class PolicyTests(unittest.TestCase):
    def test_single_tuple_and_preserved_entries(self):
        name = "policy/native_bridge_policy.v1.json"
        before = json.loads((HERE / "sources/baseline/policy" / name).read_text())
        after = json.loads((HERE / "sources/candidate/policy" / name).read_text())
        extra = after["system_libraries"].pop()
        self.assertEqual(extra, dict(soname="libmedia_jni.so", path="/system/android/lib64/liboh_android_runtime.so"))
        self.assertEqual(before, after)
        self.assertEqual(len(before["shared_sonames"]), 7)

    def test_alternate_runtime_alias_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch) / "policy"
            shutil.copytree(HERE / "sources/candidate/policy", root)
            path = root / "policy/native_bridge_policy.v1.json"
            header = root / "include/nativeloader/native_bridge_policy.h"
            path.write_text(path.read_text().replace("libmedia_jni.so", "libother_jni.so"))
            header.write_text(header.read_text().replace("libmedia_jni.so", "libother_jni.so"))
            result = subprocess.run(["python3", root / "tests/verify_bridge_policy.py"], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("system library path is not exact", result.stderr)

    def test_resident_only_and_normal_loader_behavior(self):
        with tempfile.TemporaryDirectory() as scratch:
            tree = HERE / "sources/candidate/policy"
            binary = Path(scratch) / "test-owner"
            subprocess.run(["clang++", "-std=c++17", "-O2", "-Werror", "-pthread",
                "-include", HERE / "test_platform.h",
                "-I" + str(tree / "include"), "-I" + str(tree / "src"),
                "-I" + str(HERE / "sources/build-support/dependencies"),
                HERE / "test_owner.cpp", tree / "src/system_loader.cpp", "-o", binary], check=True)
            subprocess.run([binary], check=True)


class RouteTests(unittest.TestCase):
    def test_exact_one_whitelist_entry(self):
        before = (HERE / "sources/baseline/host/zlib-route.h").read_text()
        after = (HERE / "sources/candidate/host/zlib-route.h").read_text()
        self.assertEqual(before, after.replace(', "com.mcdonalds.app"', ""))
        self.assertEqual((HERE / "sources/baseline/host/candidate-stock-host.c").read_bytes(),
                         (HERE / "sources/candidate/host/candidate-stock-host.c").read_bytes())

    def test_prefix_and_null_rejections(self):
        with tempfile.TemporaryDirectory() as scratch:
            for variant in ["baseline", "candidate"]:
                binary = Path(scratch) / ("test-routes-" + variant)
                command = ["clang", "-O2", "-Werror", "-I" + str(HERE / "sources" / variant / "host"),
                    HERE / "test_routes.c", "-o", binary]
                if variant == "baseline":
                    command.append("-DU13_BASELINE_EXPECT_NO_MCD")
                subprocess.run(command, check=True)
                subprocess.run([binary], check=True)


class EvidenceTests(unittest.TestCase):
    def test_build_receipts_and_consumer_limits(self):
        for role in ["policy", "host"]:
            record = json.loads((HERE / (role + "-build-receipt.json")).read_text())
            self.assertTrue(record["exact_u12_baseline"])
            self.assertTrue(record["two_builds_identical"])
            self.assertEqual(record["artifacts"]["candidate1"]["sha256"], record["artifacts"]["candidate2"]["sha256"])
        consumer = json.loads((HERE / "consumer.json").read_text())
        self.assertEqual(consumer["consumer_sha256"], "b7efab7537ed532ecca1dca6fe18878f4f06f3bc78b9fba65a69ed53ba8f1e1c")
        self.assertEqual(consumer["zlib_missing"], [])
        self.assertIn("not proof", consumer["limitation"])
        for role in ["policy", "host"]:
            abi = json.loads((HERE / "evidence" / ("abi-" + role + ".json")).read_text())
            for field in ["removed", "added", "drift", "call_diffs", "consumer_breaks"]:
                self.assertEqual(abi[field], [])
        namespace = json.loads((HERE / "namespace-gates.json").read_text())
        for gate in ["N1", "N2"]:
            self.assertTrue(namespace["delta"][gate]["structurally_identical"])
            self.assertEqual(namespace["delta"][gate]["new"], [])
        predictions = json.loads((HERE / "predictions.json").read_text())
        row = next(value for value in predictions["rows"] if value["key"] == "mcdonalds")
        self.assertEqual(row["incremental_over_u12"], 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", choices=["policy", "route", "evidence"])
    args = parser.parse_args()
    suites = {"policy": PolicyTests, "route": RouteTests, "evidence": EvidenceTests}
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(value)
        for key, value in suites.items() if args.part is None or key == args.part)
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
