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


class EvidenceTests(unittest.TestCase):
    def test_two_provider_names_and_source_provenance(self):
        rows = {row["key"]: row for row in load("observations.json")["rows"]}
        self.assertEqual(rows["subwaysurfers"]["pids"], [3245])
        self.assertEqual(rows["cv2-com-chessclock-android"]["pids"], [2315])
        dex = json.dumps(load("evidence/MediaPlayer-clinit.json"))
        self.assertIn("media_jni", dex)
        self.assertIn("native_init", dex)
        self.assertIn("libmediandk.so", (HERE / "evidence/subwaysurfers-hilog.txt").read_text())
        sources = load("sources.json")
        self.assertEqual(sources["commit"], "402dbe885fd58af75e4c1d7e790fbf4bb22f29f9")
        self.assertEqual(len(sources["files"]), 65)
        for row in sources["files"]:
            self.assertEqual(hashlib.sha256((HERE / row["snapshot"]).read_bytes()).hexdigest(), row["sha256"])
        prediction = load("predictions.json")
        self.assertEqual(prediction["conditional_first_wall_movement"], 1)
        self.assertFalse(prediction["rows"][1]["conditional_first_wall_moved"])
        self.assertTrue(all(row["t20"] == "unknown" for row in prediction["rows"]))


class ProviderTests(unittest.TestCase):
    def test_actual_api_coverage_and_admission_boundary(self):
        api = load("api.json")
        self.assertEqual(api["imported_count"], 50)
        exports = set(load("build-receipt.json")["exports"])
        self.assertEqual(exports, {row["symbol"] for row in api["apis"]} | {"AMediaFormat_new", "westlake_mediandk_presence_provenance"})
        for name in ["abi-mediandk", "abi-policy-candidate", "abi-policy-rebuild"]:
            report = load("evidence/" + name + ".json")
            for field in ["removed", "drift", "consumer_breaks", "call_diffs"]:
                self.assertEqual(report[field], [])
        gate = load("namespace-gates.json")
        self.assertEqual((gate["baseline_status"], gate["candidate_status"]), ("PASS", "REJECT"))
        self.assertTrue(gate["n2_findings_identical"])
        self.assertEqual(gate["n2_count"], 103)
        self.assertEqual(gate["candidate_new_n1"], [])
        self.assertFalse(gate["rollout_ready"])
        self.assertFalse(load("offline_precheck.json")["execution_enabled"])
        policy = load("policy-receipt.json")
        self.assertEqual(policy["original"]["shared_sonames"], policy["candidate"]["shared_sonames"])
        self.assertEqual(len(policy["candidate"]["system_libraries"]), 6)
        self.assertIn("libsoundpool.so", [row["soname"] for row in policy["candidate"]["system_libraries"]])
        self.assertTrue(policy["repeat_semantics_identical"])
        self.assertEqual(load("provider-closure.json")["unresolved"], [])

    def test_source_compiles_and_typed_failures_without_artifacts(self):
        compiler = shutil.which("clang")
        if compiler is None:
            self.skipTest("host clang unavailable; admitted C fixture requires a host compiler, not ignored artifacts")
        with tempfile.TemporaryDirectory(prefix="u12-mediandk-host-") as scratch:
            output = Path(scratch) / "fixture"
            command = [compiler, "-std=c11", "-D_GNU_SOURCE", "-O2", "-Werror", "-I" + str(HERE),
                       "-I" + str(HERE / "inputs/public-types"), "-I" + str(HERE / "inputs/aosp14/media/ndk/include"),
                       str(HERE / "test_provider.c"), "-o", str(output)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            result = subprocess.run([str(output)], check=True, capture_output=True, text=True)
            self.assertIn("unsupported=-10002", result.stdout)
            self.assertIn("typed media boundary PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
