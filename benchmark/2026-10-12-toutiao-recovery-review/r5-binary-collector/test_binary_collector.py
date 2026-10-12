import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import binary_safe_collector as binary


class BinaryCollectorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="r5-binary-local-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.raw = b"org.westlake.imehost\0\0extra\0"
        self.board_sha = hashlib.sha256(self.raw).hexdigest()
        self.encoded = b" " + self.raw.hex(" ").encode() + binary.SHA_MARKER + self.board_sha.encode() + b"  /proc/4344/cmdline\n"

    def run_read(self, encoded=None, host_rc=0, remote_rc=0, marker=True, kind="host_cmdline", command="cat /proc/4344/cmdline"):
        collector = binary.BinarySafeCollector(sys.executable, "61b0657200000000000000000324012c", self.root / "raw")
        def transport(argv, **kwargs):
            token = re.search(r"__EXACT_READ_RC_[0-9a-f]+__", argv[-1])[0]
            output = self.encoded if encoded is None else encoded
            output += b"\n" + token.encode() + str(remote_rc).encode() + b"\n" if marker else b""
            return subprocess.CompletedProcess(argv, host_rc, output, b"")
        with patch.object(binary.original.subprocess, "run", side_effect=transport):
            result = collector.read(kind, command)
        return result, collector

    def test_nul_bytes_logical_read_and_actual_transport_preserved(self):
        (raw, reading), collector = self.run_read()
        self.assertEqual(raw, self.raw)
        self.assertEqual(reading["command"], "cat /proc/4344/cmdline")
        decoded = collector.directory / reading["stdout"]["path"]
        self.assertEqual(decoded.read_bytes(), self.raw)
        evidence = json.loads((collector.directory / reading["binary_transport"]["path"]).read_text())
        self.assertEqual(evidence["board_sha256"], self.board_sha)
        self.assertTrue(evidence["accepted"])
        self.assertIn("od -An -v -tx1", evidence["actual_argv"][-1])
        self.assertEqual(evidence["adapter"]["sha256"], binary.digest(binary.__file__))
        self.assertEqual(json.loads((collector.directory / "000-host_cmdline.json").read_text())["command"], evidence["encoded_command"])

    def test_real_275_byte_probe_matches_board_sha(self):
        source = binary.WORKSPACES / "westlake-harness/benchmark/2026-10-12-v1-seal-execution/61b-binary-read-probe/001-encoded-cmdline.stdout"
        text = source.read_bytes()
        matched = re.search(rb"(?m)^([0-9a-f]{64})  /proc/4344/cmdline$", text)
        self.assertIsNotNone(matched)
        adapted = text[:matched.start()] + binary.SHA_MARKER + matched[0] + b"\n"
        raw, sha = binary.decode_hex(adapted, "/proc/4344/cmdline")
        self.assertEqual(len(raw), 275)
        self.assertEqual(sha, "02d57f611f6aeb98c4c796a5925fff85f8907113ab924b42c66f5aa0d6ddbf5c")
        self.assertEqual(raw.split(b"\0")[0], b"org.westlake.imehost")

    def test_original_strict_validator_accepts_decoded_nul(self):
        import test_observations
        fixture = test_observations.ObservationTests("test_running_raw_identity_matches")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        expected, data = fixture.fixture("running")
        fixture.replace_raw(data, "host_cmdline", self.raw)
        result = fixture.validate(expected, data, "running")
        self.assertEqual(result["window_id"], 33)
        fixture.replace_raw(data, "host_cmdline", b"org.westlake.imehost")
        with self.assertRaisesRegex(ValueError, "NUL"):
            fixture.validate(expected, data, "running")

    def test_malformed_hex_wrong_sha_path_and_duplicate_marker_reject(self):
        for encoded in (self.encoded.replace(b" 6f ", b" 6 ", 1),
                        self.encoded.replace(self.board_sha.encode(), b"0" * 64),
                        self.encoded.replace(b"/proc/4344/", b"/proc/4345/"),
                        self.encoded + binary.SHA_MARKER,
                        self.encoded.replace(b" 6f ", b" * ", 1)):
            with self.subTest(encoded=encoded), self.assertRaises(ValueError):
                binary.decode_hex(encoded, "/proc/4344/cmdline")

    def test_host_or_remote_failure_cannot_emit_decoded_success(self):
        for host, remote, marker in ((7, 0, True), (0, 7, True), (0, 0, False)):
            with self.subTest(case=(host, remote, marker)), tempfile.TemporaryDirectory(prefix="r5-failure-") as directory:
                self.root = Path(directory)
                with self.assertRaises(ValueError):
                    self.run_read(host_rc=host, remote_rc=remote, marker=marker)
                self.assertFalse(list((self.root / "raw").glob("*.decoded.stdout")))

    def test_other_kind_uses_original_command_and_bytes(self):
        (raw, reading), collector = self.run_read(encoded=b"BOOT_UUID\n", kind="boot_before", command="cat /proc/sys/kernel/random/boot_id")
        self.assertEqual(raw, b"BOOT_UUID\n")
        self.assertNotIn("binary_transport", reading)
        self.assertNotIn("od -", collector.commands[0]["argv"][-1])

    def test_noncanonical_logical_cmdline_refuses_before_transport(self):
        collector = binary.BinarySafeCollector(sys.executable, "61b0657200000000000000000324012c", self.root / "raw")
        with patch.object(binary.original.subprocess, "run", side_effect=AssertionError("transport forbidden")):
            for command in ("cat /proc/1/cmdline", "cat /proc/4344/cmdline; true", "strings /proc/4344/cmdline"):
                with self.assertRaises(ValueError):
                    collector.read("host_cmdline", command)

    def test_both_entry_modes_and_r3_frozen_selection_inject_same_class(self):
        import contextlib
        import io
        import selfcheck_entry
        for mode in ("realization", "activation"):
            with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    selfcheck_entry.main(["--checker", mode, "--help"])
                self.assertEqual(stopped.exception.code, 0)
        checker = sys.modules["r5_activation_selfcheck"]
        proof = binary.WORKSPACES / "westlake-harness/benchmark/2026-10-12-v1-seal-execution/exact-5cd-placement/realization.json"
        checker.select_frozen(proof)
        self.assertIs(checker.original_check.ReadOnlyCollector, binary.BinarySafeCollector)
        self.assertEqual(binary.digest(checker.original_check.__file__), binary.PINS["selfcheck"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
