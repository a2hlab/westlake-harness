import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent


def module(filename):
    spec = importlib.util.spec_from_file_location(filename.stem, filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


GATE = module(HERE / "gate.py")


class EvidenceTests(unittest.TestCase):
    def test_source_identity(self):
        receipt = module(HERE / "build.py").verify_sources()
        self.assertEqual(len(receipt["files"]), 30)
        self.assertEqual(receipt["new_exports"], ["android_dlopen_ext", "__gnu_strerror_r"])

    def test_abi_reports(self):
        baseline = json.loads((HERE / "evidence/baseline-abi.json").read_text())
        candidate = json.loads((HERE / "evidence/candidate-abi.json").read_text())
        self.assertTrue(GATE.validate(baseline, set()))
        self.assertTrue(GATE.validate(candidate, GATE.NEW_EXPORTS))
        self.assertGreaterEqual(len(candidate["consumers"]), 4)
        consumers = json.loads((HERE / "consumers.json").read_text())["apps"]
        self.assertEqual(len(consumers), 4)
        inventory = {member["file"]: member["sha256"] for application in consumers for member in application["members"]}
        self.assertEqual(len(inventory), 12)
        self.assertEqual(inventory, {row["file"]: row["sha256"] for row in candidate["consumers"]})
        self.assertEqual(baseline["old"], candidate["old"])
        receipt = json.loads((HERE / "evidence/build-receipt.json").read_text())
        self.assertEqual(receipt["artifacts"]["baseline"], baseline["new"]["sha256"])
        self.assertEqual(receipt["artifacts"]["candidate"], candidate["new"]["sha256"])
        self.assertFalse(receipt["ppsspp_namespace_fixed"])

    def test_gate_rejects_mutations(self):
        original = json.loads((HERE / "evidence/candidate-abi.json").read_text())
        for field in ["removed", "drift", "consumer_breaks", "call_diffs", "added"]:
            mutated = copy.deepcopy(original)
            mutated[field].append("unexpected")
            with self.subTest(field=field), self.assertRaises(ValueError):
                GATE.validate(mutated, GATE.NEW_EXPORTS)
        with self.assertRaises(ValueError):
            GATE.validate({}, GATE.NEW_EXPORTS)

    def test_caller_tail_branch_and_weak_backend(self):
        assembly = (HERE / "evidence/candidate-dlext.asm").read_text()
        self.assertRegex(assembly, r"\bb\s+[^\n]*<dlopen@plt>")
        self.assertRegex(assembly, r"ldp\s+x29, x30")
        self.assertRegex(assembly, r"mov\s+x3, x30")
        symbols = (HERE / "evidence/candidate-symbols.txt").read_text()
        self.assertRegex(symbols, r"WEAK\s+DEFAULT\s+UND __loader_android_dlopen_ext")

    def test_provenance_and_ppsspp_scope(self):
        provenance = json.loads((HERE / "provenance.json").read_text())
        self.assertEqual(provenance["aosp_tag"], "android-14.0.0_r1")
        self.assertEqual([row["flags"] for row in provenance["ppsspp_calls"]], ["0x200", "0x210"])
        self.assertFalse(provenance["ppsspp_fixed"])
        self.assertFalse(provenance["meet_visibility_fixed"])
        self.assertEqual(provenance["abort_owner"], "baseline/src/abort_message_compat.cpp")
        for entry in provenance["evidence"]:
            self.assertEqual(hashlib.sha256((HERE / entry["path"]).read_bytes()).hexdigest(), entry["sha256"])


class HostFixtures(unittest.TestCase):
    def setUp(self):
        if sys.platform != "darwin":
            self.skipTest("host fixtures require Darwin POSIX strerror_r; OHOS build is separate")
        self.temporary = tempfile.TemporaryDirectory(prefix="u10-shim-test-")
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)

    def compile_run(self, name, sources, arguments=(), extra=(), compiler="/usr/bin/cc"):
        executable = self.output / name
        subprocess.run([compiler, "-O0", "-g", "-pthread", *extra, *map(str, sources), "-o", str(executable)], check=True)
        result = subprocess.run([str(executable), *map(str, arguments)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result


class BehaviorTests(HostFixtures):
    def test_gnu_buffer_errno_and_threads(self):
        self.compile_run("gnu", [HERE / "tests/gnu.c", HERE / "overlay/gnu_strerror_r.c"])

    def test_abort_single_owner_first_message(self):
        sources = [HERE / "tests/abort.cpp", HERE / "baseline/src/abort_message_compat.cpp"]
        self.compile_run("abort", sources, extra=["-std=gnu++17"], compiler="/usr/bin/clang++")
        self.compile_run("abort-null", sources, arguments=["null"], extra=["-std=gnu++17"], compiler="/usr/bin/clang++")


class LoaderTests(HostFixtures):
    def test_absent_backend_rejects_ppsspp_flags(self):
        result = self.compile_run("absent", [HERE / "tests/loader_absent.c", HERE / "overlay/android_dlopen_ext.c"], extra=["-Wl,-U,___loader_android_dlopen_ext"])
        self.assertIn("flags=0x200", result.stderr)
        self.assertIn("flags=0x210", result.stderr)
        self.assertEqual(result.stderr.count("[U10-DLEXT]"), 4)

    def test_real_ordinary_load_and_dlerror(self):
        library = self.output / "fixture.dylib"
        subprocess.run(["/usr/bin/cc", "-dynamiclib", str(HERE / "tests/library.c"), "-o", str(library)], check=True)
        self.compile_run("real", [HERE / "tests/loader_real.c", HERE / "overlay/android_dlopen_ext.c"], arguments=[library], extra=["-Wl,-U,___loader_android_dlopen_ext"])

    def test_real_backend_preserves_caller_and_extinfo(self):
        self.compile_run("backend", [HERE / "tests/loader_backend.c", HERE / "overlay/android_dlopen_ext.c"])


if __name__ == "__main__":
    unittest.main()
