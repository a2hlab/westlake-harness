#!/usr/bin/env python3
"""Guard the explicit-origin contract for the ARM64 runtime input freeze."""

from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid


SCRIPT = Path(__file__).with_name("import_inputs.sh")
PROVENANCE_WRITER = Path(__file__).with_name("write_frozen_provenance.py")


class ImportInputsContractTest(unittest.TestCase):
    def test_shell_is_valid(self):
        subprocess.run(["bash", "-n", str(SCRIPT)], check=True)

    def test_missing_origins_fail_closed_before_a_historical_copy(self):
        root = SCRIPT.parents[3]
        environment = {
            "WESTLAKE_ARM64_RUNTIME_ROOT": str(
                root / ".work" / f"contract-no-origin-{uuid.uuid4().hex}"
            )
        }
        result = subprocess.run(
            ["bash", str(SCRIPT)], text=True, capture_output=True, env=environment
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("WESTLAKE_OH_ORIGIN is required", result.stderr)

    def test_no_deleted_workstation_origin_is_embedded(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("/opt/10.Project/16-WestLake", source)
        self.assertNotIn("/opt/21.Game/scratchpad", source)
        self.assertIn("WESTLAKE_ROM_ORIGIN", source)
        self.assertIn("WESTLAKE_AIDL_ORIGIN", source)
        self.assertIn('"$TOOL_ORIGIN/bin/llvm-nm"', source)
        self.assertIn("rsync -a --exclude='.git'", source)

    def test_single_process_provenance_writer_records_matching_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            origin = root / "origin.txt"
            frozen = root / "frozen"
            local = frozen / "nested" / "input.txt"
            origin.write_text("same bytes\n", encoding="utf-8")
            local.parent.mkdir(parents=True)
            local.write_text("same bytes\n", encoding="utf-8")
            mappings = root / "mappings.tsv"
            mappings.write_text(
                f"source\tnested/input.txt\t{origin}\tBUILD_INPUT\n",
                encoding="utf-8",
            )
            provenance = root / "provenance.tsv"
            local_hashes = root / "frozen.sha256"
            subprocess.run(
                ["python3", str(PROVENANCE_WRITER), "--mappings", str(mappings),
                 "--frozen", str(frozen), "--provenance", str(provenance),
                 "--local-hashes", str(local_hashes)],
                check=True,
            )
            self.assertIn("nested/input.txt", provenance.read_text(encoding="utf-8"))
            self.assertIn("nested/input.txt", local_hashes.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
