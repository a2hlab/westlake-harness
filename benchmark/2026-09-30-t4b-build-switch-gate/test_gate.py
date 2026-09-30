#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKSPACES = Path(os.environ.get("WORKSPACES", ROOT.parent))
SCRIPT = ROOT / "knowledge/toolchains/art-r155/t4b_build_switch_gate.py"
SPEC = importlib.util.spec_from_file_location("t4b_gate", SCRIPT)
sys.path.insert(0, str(SCRIPT.parent))
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
BASE = WORKSPACES / "westlake-generation-v3c-candidate/payload/android"
LIBART = BASE / "lib64/libart.so"
OAT = BASE / "framework/arm64/boot.oat"
T5 = WORKSPACES / "_hw248-t5/arm64/boot.oat"
REFERENCE_SHA = "25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c"
T5_SHA = "08837079ac97bbec25a804fc1916e5973911b8dd58733a57f8e5f52d5c9da6c9"
T5B_SHA = "90f827190482b849f71bceb9ab3d2482c8b42adf70b8b084af887728cb43f248"


def receipt(oat=OAT, libart=LIBART):
    return dict(schema=1, evidence_kind="synthetic_fixture",
                artifacts=dict(libart_sha256=gate.sha(libart.read_bytes()),
                               boot_oat_sha256=gate.sha(oat.read_bytes())),
                environment={key: gate.R155[flag] for key, flag in gate.ENVIRONMENT.items()},
                native_debug_build=False)


def write_receipt(directory, value, suffix=""):
    path = Path(directory) / "BUILD.md"
    path.write_text("# SYNTHETIC TEST FIXTURE, NOT HISTORICAL BUILD EVIDENCE\n\n"
                    "```t4b-build-json\n" + json.dumps(value) + "\n```\n" + suffix)
    return path


class ReferenceTests(unittest.TestCase):
    def test_native_binary_predicates(self):
        data = LIBART.read_bytes()
        self.assertEqual(gate.sha(data), gate.LIBART_SHA)
        actual, anchors = gate.native_flags(data)
        self.assertEqual(actual, gate.R155)
        self.assertEqual(len(anchors), 8)

    def test_real_v3c_known_consistency_pass(self):
        self.assertEqual(gate.sha(OAT.read_bytes()), REFERENCE_SHA)
        result = gate.check(LIBART, OAT)
        self.assertEqual(result["consistency"], "pass")
        self.assertEqual(result["observations"]["oat"], {"read_barrier": False})
        self.assertEqual(result["verdict"], "pending_review")
        self.assertFalse(result["deploy_allowed"])

    def test_complete_fixture_pass_is_not_historical_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            build = write_receipt(directory, receipt())
            result = gate.check(LIBART, OAT, build)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["exceptions"], [])
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["receipt_kind"], "synthetic_fixture")
        self.assertFalse(result["deploy_allowed"])
        self.assertNotIn("bootclasspath-checksums", result["oat"]["kv"])
        self.assertNotIn("compilation-reason", result["oat"]["kv"])


class T5bTests(unittest.TestCase):
    def test_actual_t5b_three_way_values_match_with_four_receipt_exceptions(self):
        directory = WORKSPACES / "_hw248-t5b/arm64"
        manifest = HERE / "evidence/T5b-SHA256SUMS.txt"
        rows = [line.split() for line in manifest.read_text().splitlines()]
        self.assertEqual(len(rows), 27)
        self.assertEqual(len({row[1] for row in rows}), 27)
        for expected, name in rows:
            self.assertEqual(Path(name).name, name)
            self.assertEqual(gate.sha((directory / name).read_bytes()), expected)
        self.assertEqual(gate.sha((directory / "boot.oat").read_bytes()), T5B_SHA)
        result = gate.check(LIBART, directory / "boot.oat", HERE / "evidence/T3b-BUILD-final-snapshot.md")
        self.assertEqual(result["consistency"], "pass")
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(len(result["comparisons"]), 7)
        self.assertTrue(all(row["equal"] for row in result["comparisons"]))
        self.assertEqual(result["exit_code"], 3)
        self.assertEqual({row["field"] for row in result["exceptions"]},
                         {"build.receipt", "build.libart_sha256", "build.boot_oat_sha256", "build.native_debug_build"})


class MismatchTests(unittest.TestCase):
    def test_t5_actual_mismatch_wins_over_missing_receipt(self):
        self.assertEqual(gate.sha(T5.read_bytes()), T5_SHA)
        result = gate.check(LIBART, T5)
        self.assertEqual(result["exit_code"], 2)
        self.assertEqual(result["consistency"], "fail")
        self.assertTrue(result["exceptions"])
        self.assertTrue(any(row.get("field") == "read_barrier" and
                            row.get("left") is False and row.get("right") is True
                            for row in result["mismatches"]))

    def test_every_required_build_switch_mismatch(self):
        for variable, flag in gate.ENVIRONMENT.items():
            with self.subTest(variable=variable), tempfile.TemporaryDirectory() as directory:
                value = receipt()
                value["environment"][variable] = "CMC" if flag == "default_gc" else True
                result = gate.check(LIBART, OAT, write_receipt(directory, value))
                self.assertEqual(result["exit_code"], 2)
                self.assertTrue(any(row["field"] == flag for row in result["mismatches"]))

    def test_native_debug_mismatch_not_hidden_by_oat_debuggable_false(self):
        with tempfile.TemporaryDirectory() as directory:
            value = receipt()
            value["native_debug_build"] = True
            result = gate.check(LIBART, OAT, write_receipt(directory, value))
        self.assertEqual(result["oat"]["kv"]["debuggable"], "false")
        self.assertEqual(result["exit_code"], 2)

    def test_unstructured_mismatch_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "BUILD.md"
            path.write_text("```sh\nexport ART_USE_READ_BARRIER=true\n```\n")
            result = gate.check(LIBART, OAT, path)
        self.assertEqual(result["exit_code"], 2)

    def test_shell_receipt_contradiction_and_duplicate_assignments(self):
        for suffix in ["\n```sh\nexport ART_USE_READ_BARRIER=true\n```\n",
                       "\n```sh\nexport ART_DEFAULT_GC_TYPE=CMS\nART_DEFAULT_GC_TYPE=CMC\n```\n"]:
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                result = gate.check(LIBART, OAT, write_receipt(directory, receipt(), suffix))
                self.assertEqual(result["exit_code"], 2)


class UnknownTests(unittest.TestCase):
    def test_missing_and_unstructured_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "BUILD.md"
            for contents in [None, "# Old record\nNo environment was retained.\n"]:
                if contents:
                    path.write_text(contents)
                result = gate.check(LIBART, OAT, path)
                self.assertEqual(result["exit_code"], 3)
                self.assertEqual(result["consistency"], "pass")
                self.assertTrue(result["exceptions"])
                self.assertFalse(result["deploy_allowed"])

    def test_each_missing_required_value_is_unknown(self):
        for variable in gate.ENVIRONMENT:
            with self.subTest(variable=variable), tempfile.TemporaryDirectory() as directory:
                value = receipt()
                del value["environment"][variable]
                result = gate.check(LIBART, OAT, write_receipt(directory, value))
                self.assertEqual(result["exit_code"], 3)
                self.assertTrue(result["exceptions"])

    def test_unknown_libart_not_assumed_r155(self):
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory) / "libart.so"
            data = bytearray(LIBART.read_bytes())
            data[16] ^= 1
            native.write_bytes(data)
            value = receipt(libart=native)
            result = gate.check(native, OAT, write_receipt(directory, value))
        self.assertEqual(result["exit_code"], 3)
        self.assertEqual(result["consistency"], "unknown")
        self.assertEqual(result["observations"]["libart"], {})

    def test_missing_read_barrier_kv_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "boot.oat"
            data = OAT.read_bytes().replace(b"concurrent-copying\0", b"unrecorded-copying\0")
            image.write_bytes(data)
            result = gate.check(LIBART, image, write_receipt(directory, receipt(oat=image)))
        self.assertEqual(result["exit_code"], 3)
        self.assertTrue(any(row["field"] == "oat.concurrent-copying" for row in result["exceptions"]))


class IntegrityTests(unittest.TestCase):
    def test_ninja_macro_mentions_are_not_environment_assignments(self):
        with tempfile.TemporaryDirectory() as directory:
            build = write_receipt(directory, receipt(),
                                  "\nNinja contained ART_USE_READ_BARRIER=1 zero times.\n")
            self.assertEqual(gate.check(LIBART, OAT, build)["exit_code"], 0)

    def test_shell_comments_echo_and_continuations(self):
        with tempfile.TemporaryDirectory() as directory:
            build = write_receipt(directory, receipt(),
                                  "\n```sh\n# ART_USE_READ_BARRIER=true\n"
                                  "echo 'ART_HEAP_POISONING=true'\n"
                                  "export ART_USE_READ_BARRIER=false \\\n"
                                  " ART_DEFAULT_GC_TYPE='CMS'\n```\n")
            self.assertEqual(gate.check(LIBART, OAT, build)["exit_code"], 0)

    def test_malformed_receipts_never_pass(self):
        for value in [[], {"schema": True}, {"schema": 1, "environment": []},
                      {"schema": 1, "artifacts": []}]:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                result = gate.check(LIBART, OAT, write_receipt(directory, value))
                self.assertEqual(result["exit_code"], 2)
        for body in ['{"schema":1,"schema":2}', '{bad json',
                     '{}\n```\n```t4b-build-json\n{}']:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "BUILD.md"
                path.write_text("```t4b-build-json\n" + body + "\n```\n")
                self.assertEqual(gate.check(LIBART, OAT, path)["exit_code"], 2)

    def test_valid_receipt_mode_and_string_booleans(self):
        with tempfile.TemporaryDirectory() as directory:
            value = receipt()
            value["evidence_kind"] = "build_receipt"
            for variable, flag in gate.ENVIRONMENT.items():
                if flag != "default_gc":
                    value["environment"][variable] = "false"
            result = gate.check(LIBART, OAT, write_receipt(directory, value))
        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["deploy_allowed"])
        self.assertEqual(result["deploy_allowed_scope"], "T4b permits only; T4 layout and T6 gates still required")

    def test_receipt_identity_mismatch_and_missing_full_sha(self):
        for bad_value, expected in [("0" * 64, 2), ("25d92cf7", 2), (None, 3)]:
            with self.subTest(value=bad_value), tempfile.TemporaryDirectory() as directory:
                value = receipt()
                if bad_value is None:
                    del value["artifacts"]["boot_oat_sha256"]
                else:
                    value["artifacts"]["boot_oat_sha256"] = bad_value
                result = gate.check(LIBART, OAT, write_receipt(directory, value))
                self.assertEqual(result["exit_code"], expected)

    def test_invalid_boolean_is_not_false_and_duplicate_json_rejected(self):
        for bad_value in ["unknown", 0, None, "False"]:
            with self.subTest(value=bad_value), tempfile.TemporaryDirectory() as directory:
                value = receipt()
                value["environment"]["ART_HEAP_POISONING"] = bad_value
                self.assertEqual(gate.check(LIBART, OAT, write_receipt(directory, value))["exit_code"], 2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            json.loads('{"schema":1,"schema":2}', object_pairs_hook=gate.unique_object)

    def test_corrupt_oat_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boot.oat"
            for contents in [b"", b"oat\n230\0", OAT.read_bytes()[:100]]:
                path.write_bytes(contents)
                self.assertEqual(gate.check(LIBART, path)["exit_code"], 2)
            self.assertEqual(gate.check(Path(directory) / "missing.so", OAT)["exit_code"], 2)
            data = bytearray(OAT.read_bytes())
            struct.pack_into("<I", data, 4096 + 64, 0xffffffff)
            path.write_bytes(data)
            self.assertEqual(gate.check(LIBART, path)["exit_code"], 2)

    def test_cli_stdout_file_and_input_protection(self):
        before = {path: gate.sha(path.read_bytes()) for path in [LIBART, OAT, T5]}
        with tempfile.TemporaryDirectory() as directory:
            build = write_receipt(directory, receipt())
            output = Path(directory) / "report.json"
            command = [sys.executable, str(SCRIPT), "--libart", str(LIBART), "--oat", str(OAT),
                       "--build", str(build)]
            completed = subprocess.run(command + ["--out", str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout), json.loads(output.read_text()))
            output_before = output.read_bytes()
            for target in [output, OAT, build]:
                completed = subprocess.run(command + ["--out", str(target)], capture_output=True, text=True)
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertFalse(json.loads(completed.stdout)["deploy_allowed"])
            self.assertEqual(output.read_bytes(), output_before)
        self.assertEqual({path: gate.sha(path.read_bytes()) for path in before}, before)

    def test_cli_actual_t5_and_reference_exit_codes(self):
        for image, expected in [(T5, 2), (OAT, 3)]:
            completed = subprocess.run([sys.executable, str(SCRIPT), "--libart", str(LIBART),
                                        "--oat", str(image)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, expected, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["exit_code"], expected)

    def test_shared_kv_reader_reuse_and_prefix_false_positive_rejection(self):
        result = gate.check(LIBART, OAT)
        self.assertEqual(result["kv_reader"], "check_boot_oat_rb.read_kv (cc-wiki 785fdaf1b)")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boot.oat"
            data = bytearray(OAT.read_bytes())
            bait = b"concurrent-copying\0true\0"
            data[512:512 + len(bait)] = bait
            path.write_bytes(data)
            self.assertEqual(gate.read_kv(path)[1]["concurrent-copying"], "true")
            result = gate.check(LIBART, path)
        self.assertEqual(result["exit_code"], 2)
        self.assertTrue(any("shared KV reader" in row.get("error", "") for row in result["mismatches"]))


if __name__ == "__main__":
    unittest.main()
