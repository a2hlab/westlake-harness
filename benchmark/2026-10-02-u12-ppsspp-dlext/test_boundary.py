import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


class Boundary(unittest.TestCase):
    def test_real_flags_are_not_force_load_or_zero(self):
        result = json.loads((HERE / "results.json").read_text())
        self.assertEqual([row["flags"] for row in result["calls"]], ["0x200", "0x210"])
        self.assertIn("USE_LIBRARY_FD", result["calls"][1]["semantics"])
        self.assertEqual(result["standalone_first_fatal_move"], 0)
        self.assertFalse(result["new_native_artifact"])
        self.assertFalse(result["execution_enabled"])
        self.assertIn("android_dlopen_ext@LIBC", (HERE / "evidence/consumer-target-symbols.txt").read_text())

    def test_unimplemented_backend_is_faithfully_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "test_refusal"
            command = ["clang", "-std=c11", "-O2", HERE / "test_refusal.c", "-o", executable]
            if sys.platform == "darwin":
                command.append("-Wl,-U,___loader_android_dlopen_ext")
            subprocess.run(command, check=True)
            process = subprocess.run([executable], capture_output=True, text=True, check=True)
            self.assertIn("flags=0x200", process.stderr)
            self.assertIn("flags=0x210", process.stderr)


if __name__ == "__main__":
    unittest.main()
