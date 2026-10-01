import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def module(filename):
    spec = importlib.util.spec_from_file_location(filename.stem, filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def read(relative):
    return json.loads((HERE / relative).read_text())


def digest(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


class PolicyTests(unittest.TestCase):
    def test_source_and_policy(self):
        previous, shared = module(HERE / "build_loader.py").validate_policy()
        self.assertEqual(shared, previous + ["libstdc++.so"])
        self.assertNotIn("libc++.so", shared)
        source = (HERE / "native-loader/overlay/include/nativeloader/native_bridge_policy.h").read_text()
        self.assertIn("array<std::string_view, 7> kBridgeSharedSonames", source)
        self.assertEqual(source.count('"libstdc++.so"'), 1)

    def test_exact_calls_and_mutation_rejection(self):
        gate = module(HERE / "policy_gate.py")
        baseline = read("evidence/policy-baseline-abi.json")
        candidate = read("evidence/policy-candidate-abi.json")
        self.assertTrue(gate.validate(baseline))
        self.assertTrue(gate.validate(candidate, True))
        self.assertEqual(baseline["old"], candidate["old"])
        self.assertEqual(candidate["old"]["sha256"], read("evidence/u9-expected.json")["expected"]["/system/android/lib64/libnativeloader.so"])
        self.assertEqual(candidate["new"]["sha256"], read("evidence/policy-build-receipt.json")["artifacts"]["candidate"])
        self.assertTrue(candidate["consumers"])
        for field in ["removed", "added", "drift", "consumer_breaks"]:
            bad = copy.deepcopy(candidate)
            bad[field] = ["extra"]
            with self.assertRaises(ValueError):
                gate.validate(bad, True)
        bad = copy.deepcopy(candidate)
        bad["call_diffs"][0]["added_callees"].append("dlopen")
        with self.assertRaises(ValueError):
            gate.validate(bad, True)
        bad = copy.deepcopy(candidate)
        bad["call_diffs"][0]["function"] = "ResetNativeLoader"
        with self.assertRaises(ValueError):
            gate.validate(bad, True)
        bad = copy.deepcopy(candidate)
        del bad["consumer_breaks"]
        with self.assertRaises(ValueError):
            gate.validate(bad, True)

    def test_root_only_resolution(self):
        inventory = read("evidence/std-inventory.json")
        self.assertEqual(inventory["key_count"], 166)
        self.assertEqual(inventory["scanned_keys"], 166)
        self.assertEqual(inventory["unknown_keys"], [])
        self.assertEqual(inventory["bundled_std_keys"], [])
        self.assertEqual([row["bridge_soname_search_candidate"] for row in inventory["copies"]], [True, False])
        self.assertEqual(len({row["sha256"] for row in inventory["copies"]}), 1)
        self.assertNotIn("/system/android/lib64/westlake_native", inventory["bridge_search_paths"])


class VisibilityTests(unittest.TestCase):
    def test_delivered_patch_applies_exactly(self):
        relative = Path("adapter/framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_stock_host_main.c")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / relative
            target.parent.mkdir(parents=True)
            target.write_bytes((HERE / "visibility/baseline-stock-host.c").read_bytes())
            subprocess.run(["/usr/bin/patch", "-p1", "-i", str(HERE / "visibility/stock-host.patch")],
                           cwd=root, check=True, capture_output=True, text=True)
            self.assertEqual(target.read_bytes(), (HERE / "visibility/candidate-stock-host.c").read_bytes())

    def test_exact_host_and_boundary(self):
        receipt = read("evidence/host-r2/build-receipt.json")
        self.assertEqual(digest(HERE / "visibility/baseline-stock-host.c"), receipt["baseline_main_sha256"])
        self.assertEqual(digest(HERE / "visibility/candidate-stock-host.c"), receipt["candidate_main_sha256"])
        self.assertEqual(digest(HERE / "visibility/resident-compat.h"), receipt["resident_header_sha256"])
        baseline = (HERE / "visibility/baseline-stock-host.c").read_text()
        candidate = (HERE / "visibility/candidate-stock-host.c").read_text()
        recovered = candidate.replace('#include "resident-compat.h"\n', "").replace(
            "        (void)U10ShareResidentCompat(app_namespace);\n", "")
        self.assertEqual(recovered, baseline)
        gate = module(HERE / "host_gate.py")
        self.assertTrue(gate.validate(read("evidence/host-r2/baseline-abi.json")))
        report = read("evidence/host-r2/candidate-abi.json")
        self.assertTrue(gate.validate(report, True))
        self.assertEqual(report["new"]["sha256"], receipt["artifacts"]["candidate"])
        self.assertEqual(report["old"]["sha256"], read("evidence/u9-expected.json")["expected"]["/system/bin/appspawn-x"])
        bad = copy.deepcopy(report)
        bad["call_diffs"][0]["removed_callees"] = ["native_cluster_path"]
        with self.assertRaises(ValueError):
            gate.validate(bad, True)

    def test_lazy_application_view_is_not_probed(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "resident"
            subprocess.run(["/usr/bin/cc", "-O0", "-I" + str(HERE / "visibility/tests/include"),
                            str(HERE / "visibility/tests/resident.c"), "-o", str(executable)], check=True)
            result = subprocess.run([str(executable)], capture_output=True, text=True, check=True)
            self.assertIn("APPSPAWN [U10-COMPAT-VISIBLE] inherit_requested view=default", result.stderr)
            self.assertIn("inherit_requested view=westlake.sealed.child", result.stderr)
            self.assertEqual(result.stderr.count("no loading fallback"), 5)
            self.assertEqual(result.stderr.count("application_lookup=deferred"), 5)
            self.assertEqual(result.stderr.count("namespace continues"), 5)
        helper = (HERE / "visibility/resident-compat.h").read_text()
        self.assertNotIn("dlopen_ns(application", helper)
        self.assertNotIn("fprintf", helper)
        self.assertIn("APPSPAWN_LOGI", helper)
        self.assertIn("APPSPAWN_LOGE", helper)


class OpenSLESEvidenceTests(unittest.TestCase):
    def test_owner_inventory_rejects_unsafe_cast(self):
        evidence = read("opensles/owner-abi.json")
        self.assertEqual(evidence["owner_sha256"], module(HERE / "inspect_opensles.py").OWNER_SHA)
        self.assertEqual((evidence["global_count"], evidence["weak_count"], evidence["public_count"]), (122, 18, 46))
        self.assertEqual(len(evidence["exports"]), 140)
        entries = {row["name"]: row for row in evidence["exports"]}
        self.assertEqual(len(bytes.fromhex(entries["SL_IID_ENGINE"]["guid_24_bytes"])), 24)
        self.assertEqual(entries["SL_IID_BUFFERQUEUE"]["guid_24_bytes"], entries["SL_IID_OH_BUFFERQUEUE"]["guid_24_bytes"])
        self.assertEqual(entries["slCreateEngine"]["value"], "0x14350")
        self.assertEqual(evidence["instructions"][0]["bytes_little_endian"], "280000f9")
        self.assertIn("rejected", evidence["decision"])


if __name__ == "__main__":
    unittest.main()
