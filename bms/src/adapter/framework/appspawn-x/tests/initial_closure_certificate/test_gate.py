#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import unittest


HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import initial_closure_gate as gate  # noqa: E402
import build_prepare_order_evidence as phase_builder  # noqa: E402


PROJECT = gate.PROJECT_ROOT
RUN = PROJECT / "adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1"
CONFIG = RUN / "gate-config.json"
SNAPSHOT = RUN / "frozen"
TMP = HERE / ".test-work"
REFRESHED_TRIAL = (
    PROJECT
    / "adapter/research/atoms/L03/A15/evidence/runs/20260712-initial-closure-cert-r1-trial-recursive-v2-refresh-admitted"
)


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)
        TMP.mkdir(parents=True)

    def tearDown(self) -> None:
        if TMP.exists():
            shutil.rmtree(TMP)

    def test_current_generation_fails_on_independent_gates(self) -> None:
        certificate = gate.generate_certificate(CONFIG)
        self.assertEqual("FAIL_CLOSED", certificate["status"])
        codes = {item["code"] for item in certificate["errors"]}
        self.assertTrue({
            "INITIAL_CLOSURE_INCOMPLETE",
            "NEEDED_NOT_FOUND",
            "PRODUCTION_SEARCH_ORDER_NOT_PROVEN",
            "TP_SCAN_UNKNOWN",
            "TLS_PREPARE_SYMBOL_ABSENT",
            "TLS_PREPARE_ORDER_NOT_PROVEN",
            "PRE_PREPARE_SLOT5_ZERO_NOT_PROVEN",
        }.issubset(codes))
        self.assertIsNone(certificate["decision"]["pre_prepare_slot5_access_count"])
        self.assertFalse(certificate["decision"]["prepare_order_proven"])

    def test_certificate_generation_is_byte_deterministic(self) -> None:
        first = gate.stable_json_bytes(gate.generate_certificate(CONFIG))
        second = gate.stable_json_bytes(gate.generate_certificate(CONFIG))
        self.assertEqual(first, second)

    def test_raw_scanner_detects_exact_slot5_read(self) -> None:
        words = (
            0xD53BD048,  # mrs x8, tpidr_el0
            0xF9401508,  # ldr x8, [x8, #40]
            0xD65F03C0,  # ret
        )
        code = b"".join(word.to_bytes(4, "little") for word in words)
        report = gate.scan_code_bytes(code, 0x1000, 40, 8, 32)
        self.assertEqual(1, report["mrs_count"])
        self.assertEqual(1, report["slot5_access_count"])
        self.assertEqual(0, report["unknown_count"])
        access = report["sites"][0]["accesses"][0]
        self.assertEqual((40, 8, "read"), (access["offset"], access["width"], access["direction"]))

    def test_raw_scanner_detects_exact_slot5_write(self) -> None:
        words = (
            0xD53BD048,  # mrs x8, tpidr_el0
            0xF9001509,  # str x9, [x8, #40]
            0xD65F03C0,  # ret
        )
        code = b"".join(word.to_bytes(4, "little") for word in words)
        report = gate.scan_code_bytes(code, 0x1000, 40, 8, 32)
        self.assertEqual(1, report["slot5_access_count"])
        self.assertEqual("write", report["sites"][0]["accesses"][0]["direction"])

    def test_returned_tp_is_unknown_not_silent_zero(self) -> None:
        code = b"".join(word.to_bytes(4, "little") for word in (0xD53BD040, 0xD65F03C0))
        report = gate.scan_code_bytes(code, 0x2000, 40, 8, 32)
        self.assertEqual(1, report["unknown_count"])
        self.assertEqual("TP_VALUE_ESCAPES_FUNCTION", report["unknowns"][0]["reason"])

    def test_manifest_detects_mutation(self) -> None:
        snapshot = TMP / "snapshot"
        snapshot.mkdir()
        payload = snapshot / "input.bin"
        payload.write_bytes(b"original")
        manifest = gate.make_snapshot_manifest(snapshot)
        manifest_path = TMP / "manifest.json"
        manifest_path.write_bytes(gate.stable_json_bytes(manifest))
        manifest_sha = gate.sha256_file(manifest_path)
        payload.write_bytes(b"mutated")
        audit, errors = gate.validate_snapshot_manifest(snapshot, manifest_path, manifest_sha)
        self.assertFalse(audit["valid"])
        self.assertIn("SNAPSHOT_CONTENT_MISMATCH", {item["code"] for item in errors})

    def test_manifest_rejects_symlink_even_when_target_is_local(self) -> None:
        snapshot = TMP / "snapshot"
        snapshot.mkdir()
        target = snapshot / "target"
        target.write_bytes(b"x")
        (snapshot / "alias").symlink_to(target)
        with self.assertRaises(gate.GateFailure) as caught:
            gate.make_snapshot_manifest(snapshot)
        self.assertEqual("SNAPSHOT_SYMLINK", caught.exception.code)

    def test_duplicate_provider_path_is_ambiguous_even_if_bytes_match(self) -> None:
        extra = TMP / "extra"
        extra.mkdir()
        shutil.copy2(SNAPSHOT / "rootfs/system/lib64/chipset-sdk-sp/libc++.so", extra / "libc++.so")
        loader = gate.Elf64(SNAPSHOT / "rootfs/system/lib/ld-musl-aarch64.so.1")
        main = gate.Elf64(SNAPSHOT / "rootfs/system/bin/appspawn-x")
        search = [
            SNAPSHOT / "rootfs/system/android/lib64",
            SNAPSHOT / "rootfs/system/lib64/chipset-sdk-sp",
            extra,
            SNAPSHOT / "rootfs/system/lib64",
            SNAPSHOT / "rootfs/system/lib64/platformsdk",
            SNAPSHOT / "rootfs/system/lib64/chipset-sdk",
        ]
        resolver = gate.Resolver(PROJECT, loader, search)
        resolver.resolve([(main, "initial_main")])
        ambiguous = [item for item in resolver.errors if item["code"] == "NEEDED_AMBIGUOUS"]
        self.assertTrue(any(item["details"]["needed"] == "libc++.so" for item in ambiguous))

    def test_source_order_evidence_is_explicitly_rejected(self) -> None:
        evidence = TMP / "source-order.json"
        evidence.write_text(json.dumps({
            "schema": gate.SCHEMA_PHASE,
            "method": "source_order",
            "main_sha256": "not-enough",
        }))
        main = gate.Elf64(SNAPSHOT / "rootfs/system/bin/appspawn-x")
        sidecar = gate.Elf64(SNAPSHOT / "sidecars/appspawn-x.unstripped")
        config = {
            "expected_prepare_symbols": ["westlake_native_compat_prepare_main_thread"],
            "phase_evidence": {"artifact": str(evidence.relative_to(PROJECT))},
        }
        _phase, errors = gate.evaluate_phase(config, main, sidecar, [], PROJECT)
        self.assertIn("PHASE_EVIDENCE_METHOD", {item["code"] for item in errors})

    def test_main_sidecar_and_exact_loader_are_bound(self) -> None:
        certificate = gate.generate_certificate(CONFIG)
        subject = certificate["exact_subject"]
        self.assertEqual(
            "417f3f38d4ee24e32f6322e04b07a197285c7271c7e19005369740507916754a",
            subject["main"]["sha256"],
        )
        self.assertEqual(
            "316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98",
            subject["loader"]["sha256"],
        )
        self.assertTrue(subject["main_sidecar"]["valid"])

    def test_tp_report_preserves_unknown_pre_prepare_as_null(self) -> None:
        report = gate.tp_scan_report(gate.generate_certificate(CONFIG))
        self.assertEqual("westlake-initial-closure-tp-scan-v1", report["schema"])
        self.assertFalse(report["complete"])
        self.assertIsNone(report["pre_prepare_slot5_access_count"])
        self.assertFalse(report["prepare_order_proven"])

    def test_binary_callgraph_evidence_with_empty_site_set_is_accepted(self) -> None:
        refreshed_snapshot = REFRESHED_TRIAL / "frozen"
        main = gate.Elf64(refreshed_snapshot / "rootfs/system/bin/appspawn-x")
        sidecar = gate.Elf64(refreshed_snapshot / "sidecars/appspawn-x.unstripped")
        evidence = TMP / "phase.json"
        evidence.write_text(json.dumps({
            "schema": gate.SCHEMA_PHASE,
            "method": "verified_binary_callgraph_v1",
            "complete": True,
            "main_sha256": main.sha256,
            "prepare_symbol": "westlake_native_compat_prepare_main_thread",
            "slot5_sites": [],
            "pre_prepare_slot5_access_count": 0,
            "post_prepare_slot5_access_count": 0,
        }))
        config = {
            "expected_prepare_symbols": ["westlake_native_compat_prepare_main_thread"],
            "phase_evidence": {"artifact": str(evidence.relative_to(PROJECT))},
        }
        phase, errors = gate.evaluate_phase(config, main, sidecar, [], PROJECT)
        self.assertEqual([], errors)
        self.assertTrue(phase["prepare_order_proven"])
        self.assertEqual(0, phase["pre_prepare"]["slot5_access_count"])

    def test_prepare_order_builder_proves_refreshed_empty_site_set(self) -> None:
        output = TMP / "refreshed.phase.json"
        evidence = phase_builder.build_evidence(
            REFRESHED_TRIAL / "trial.gate-config.json",
            REFRESHED_TRIAL / "trial.initial-closure.tp-scan.json",
        )
        gate.write_atomic(output, gate.stable_json_bytes(evidence))
        self.assertEqual(gate.SCHEMA_PHASE, evidence["schema"])
        self.assertEqual("verified_binary_callgraph_v1", evidence["method"])
        self.assertTrue(evidence["complete"])
        self.assertEqual([], evidence["slot5_sites"])
        self.assertEqual(0, evidence["pre_prepare_slot5_access_count"])
        self.assertLess(
            evidence["exact_call_order"]["first_apply_selinux_call"],
            evidence["exact_call_order"]["first_prepare_call"],
        )

    def test_prepare_order_builder_cli_is_deterministic(self) -> None:
        first = TMP / "first.json"
        second = TMP / "second.json"
        cmd = [
            "python3",
            str(HERE / "build_prepare_order_evidence.py"),
            "--config",
            str(REFRESHED_TRIAL / "trial.gate-config.json"),
            "--tp-report",
            str(REFRESHED_TRIAL / "trial.initial-closure.tp-scan.json"),
            "--output",
        ]
        subprocess.run(cmd + [str(first)], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        subprocess.run(cmd + [str(second)], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
