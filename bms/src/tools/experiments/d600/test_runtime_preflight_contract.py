#!/usr/bin/env python3
"""Host-only tests for the D600 runtime preflight receipt contract."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("runtime_preflight_contract.py")
SPEC = importlib.util.spec_from_file_location("runtime_preflight_contract", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_receipt() -> dict[str, object]:
    artifacts = {}
    for index, (name, path) in enumerate(MODULE.REQUIRED_ARTIFACTS.items(), 1):
        digest = f"{index:064x}"
        artifacts[name] = {
            "path": path,
            "expected_sha256": digest,
            "device_sha256": digest,
        }
    return {
        "schema_version": MODULE.SCHEMA_VERSION,
        "device_serial": "61b0657200000000000000000324012c",
        "boot_id": "3b219a52-cc25-4afb-8854-0a96bf091b68",
        "artifacts": artifacts,
        "appspawn_x": {
            "pid": "3145",
            "socket_exists": True,
            "sample_window": {
                "duration_seconds": 10,
                "exit_127_count": 0,
            },
        },
        "spawn_response": {
            "result": "0x0",
            "child_pid": "3201",
        },
    }


class RuntimePreflightContractTest(unittest.TestCase):
    def assert_rejected(self, receipt: object, message: str) -> None:
        errors = MODULE.validate_receipt(receipt)
        self.assertTrue(errors, message)

    def test_valid_receipt_passes(self) -> None:
        self.assertEqual(MODULE.validate_receipt(valid_receipt()), [])

        receipt = valid_receipt()
        receipt["schema_version"] = True
        self.assert_rejected(receipt, "boolean schema version was accepted")

    def test_boot_and_device_identity_are_required(self) -> None:
        for field in ("device_serial", "boot_id"):
            with self.subTest(field=field):
                receipt = valid_receipt()
                receipt[field] = "  "
                self.assert_rejected(receipt, f"empty {field} was accepted")

    def test_all_six_artifacts_are_required_at_canonical_paths(self) -> None:
        self.assertEqual(len(MODULE.REQUIRED_ARTIFACTS), 6)
        for name in MODULE.REQUIRED_ARTIFACTS:
            with self.subTest(name=name):
                receipt = valid_receipt()
                del receipt["artifacts"][name]
                self.assert_rejected(receipt, f"missing {name} was accepted")

        receipt = valid_receipt()
        receipt["artifacts"]["libart.so"]["path"] = "/tmp/libart.so"
        self.assert_rejected(receipt, "wrong artifact path was accepted")

    def test_artifact_hashes_must_be_well_formed_and_equal(self) -> None:
        receipt = valid_receipt()
        receipt["artifacts"]["boot.art"]["device_sha256"] = "f" * 64
        self.assert_rejected(receipt, "mismatched artifact hash was accepted")

        for field in ("expected_sha256", "device_sha256"):
            with self.subTest(field=field):
                receipt = valid_receipt()
                receipt["artifacts"]["appspawn-x"][field] = "not-a-sha"
                self.assert_rejected(receipt, f"malformed {field} was accepted")

        receipt = valid_receipt()
        receipt["artifacts"]["libart.so"]["expected_sha256"] = "0" * 64
        receipt["artifacts"]["libart.so"]["device_sha256"] = "0" * 64
        self.assert_rejected(receipt, "all-zero SHA placeholders were accepted")

    def test_historical_empty_parent_pid_false_pass_is_rejected(self) -> None:
        receipt = valid_receipt()
        receipt["appspawn_x"]["pid"] = ""
        errors = MODULE.validate_receipt(receipt)
        self.assertIn("appspawn_x.pid: required positive decimal PID", errors)

    def test_parent_pid_must_be_one_positive_decimal_value(self) -> None:
        for pid in (0, -1, True, "0", "3145 3149", "[Fail] Device not found"):
            with self.subTest(pid=pid):
                receipt = valid_receipt()
                receipt["appspawn_x"]["pid"] = pid
                self.assert_rejected(receipt, f"invalid parent PID {pid!r} was accepted")

    def test_socket_and_clean_nonempty_sample_window_are_required(self) -> None:
        receipt = valid_receipt()
        receipt["appspawn_x"]["socket_exists"] = False
        self.assert_rejected(receipt, "missing socket was accepted")

        for duration in (0, -1, True, "10", float("nan"), float("inf")):
            with self.subTest(duration=duration):
                receipt = valid_receipt()
                receipt["appspawn_x"]["sample_window"]["duration_seconds"] = duration
                self.assert_rejected(receipt, f"invalid sample duration {duration!r} was accepted")

        for count in (1, 2, -1, True, "0"):
            with self.subTest(exit_127_count=count):
                receipt = valid_receipt()
                receipt["appspawn_x"]["sample_window"]["exit_127_count"] = count
                self.assert_rejected(receipt, f"invalid exit-127 count {count!r} was accepted")

    def test_spawn_response_requires_success_and_nonzero_child_pid(self) -> None:
        receipt = valid_receipt()
        receipt["spawn_response"]["result"] = "0x1"
        self.assert_rejected(receipt, "failed spawn result was accepted")

        for pid in (None, "", 0, "0", "3201 3202"):
            with self.subTest(child_pid=pid):
                receipt = valid_receipt()
                receipt["spawn_response"]["child_pid"] = pid
                self.assert_rejected(receipt, f"invalid child PID {pid!r} was accepted")

        receipt = valid_receipt()
        receipt["spawn_response"]["child_pid"] = receipt["appspawn_x"]["pid"]
        self.assert_rejected(receipt, "parent PID was accepted as the target child PID")

    def test_cli_returns_failure_for_false_pass_and_success_for_valid_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            good_path = root / "good.json"
            bad_path = root / "bad.json"
            good_path.write_text(json.dumps(valid_receipt()), encoding="utf-8")
            bad = copy.deepcopy(valid_receipt())
            bad["appspawn_x"]["pid"] = ""
            bad_path.write_text(json.dumps(bad), encoding="utf-8")

            good = subprocess.run(
                [sys.executable, str(SCRIPT), str(good_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
            self.assertIn("PASS runtime preflight", good.stdout)

            bad_result = subprocess.run(
                [sys.executable, str(SCRIPT), str(bad_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(bad_result.returncode, 1, bad_result.stdout + bad_result.stderr)
            self.assertIn("FAIL runtime preflight", bad_result.stdout)
            self.assertIn("appspawn_x.pid", bad_result.stdout)

    def test_validator_has_no_device_or_package_specific_execution(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "subprocess",
            " hdc ",
            " adb ",
            "com.example.",
            "org.fossify.",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
