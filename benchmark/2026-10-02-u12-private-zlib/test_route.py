import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


class ReviewedRoute(unittest.TestCase):
    def test_reviewed_source_and_narrow_namespace_delta(self):
        receipt = load("build-receipt.json")
        self.assertEqual(receipt["artifacts"]["candidate1"]["sha256"], receipt["artifacts"]["candidate2"]["sha256"])
        self.assertTrue(receipt["deployed_sha256"].startswith("65cc3535"))
        self.assertEqual(hashlib.sha256((HERE / "inputs/candidate-stock-host.c").read_bytes()).hexdigest(), receipt["reviewed_source_sha256"])
        for row in receipt["headers"]:
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["sha256"])
        delta = load("namespace-delta.json")
        self.assertEqual((delta["before_sites"], delta["after_sites"]), (8, 8))
        self.assertEqual(delta["new_inherit_calls"], 0)
        self.assertEqual(delta["inherit_repeat"], {"deployed": 0, "candidate": 0})
        self.assertEqual([len(delta["inherit_after_open"][name]) for name in ["deployed", "candidate"]], [4, 4])
        self.assertTrue(delta["source_keeps_original_private_branch"])
        abi = load("evidence/abi-host.json")
        self.assertEqual(abi["removed"], [])
        self.assertEqual(abi["drift"], [])
        self.assertEqual(len(abi["call_diffs"]), 1)
        self.assertEqual(abi["call_diffs"][0]["added_callees"], ["U11ZlibRoot"])
        self.assertEqual(load("consumer.json")["missing"], [])
        self.assertEqual(load("results.json")["predicted_first_fatal_moved"], 1)
        self.assertFalse(load("payload-edit.json")["execution_enabled"])

    def test_admitted_route_source_has_negative_controls_without_artifacts(self):
        compiler = shutil.which("clang")
        if compiler is None:
            self.skipTest("host clang missing; admitted-source route fixture cannot compile")
        with tempfile.TemporaryDirectory(prefix="u12-zlib-route-") as directory:
            output = Path(directory) / "test-route"
            subprocess.run([compiler, "-Werror", "-O2", "-I" + str(HERE / "inputs"), HERE / "inputs/test_routes.c", "-o", output], check=True)
            subprocess.run([output], check=True)


if __name__ == "__main__":
    unittest.main()
