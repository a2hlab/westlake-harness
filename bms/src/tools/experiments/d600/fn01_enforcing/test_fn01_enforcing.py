#!/usr/bin/env python3

import argparse
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fn01_enforcing as subject


SERIAL = "61b0657200000000000000000324012c"
BOOT_ID = "11111111-2222-3333-4444-555555555555"
BRIDGE = "/system/android/lib64/liboh_adapter_bridge.so"
EXPECTED = "a" * 64


def process(pid=10):
    return {
        "pid": pid,
        "ppid": 1,
        "uid": 0,
        "gid": 0,
        "name": "appspawn-x",
        "args": "appspawn-x",
        "selinux_context": "u:r:appspawn:s0",
        "exe": "/system/bin/appspawn-x",
        "cmdline_sha256": "b" * 64,
    }


def snapshot(run_dir: Path, phase: str, uptime: float, mode="Enforcing"):
    hilog = (
        b"01-02 10:00:00.000 1 1 I TAG: old-a\n"
        b"01-02 10:00:01.000 1 1 I TAG: old-b\n"
        b"01-02 10:00:02.000 1 1 I TAG: old-c\n"
        b"01-02 10:00:03.000 1 1 I TAG: old-d\n"
        b"01-02 10:00:04.000 1 1 I TAG: old-e\n"
        b"01-02 10:00:05.000 1 1 I TAG: old-f\n"
        b"01-02 10:00:06.000 1 1 I TAG: old-g\n"
        b"01-02 10:00:07.000 1 1 I TAG: old-h\n"
        b"01-02 10:00:08.000 1 1 I TAG: old-i\n"
        b"01-02 10:00:09.000 1 1 I TAG: old-j\n"
        b"01-02 10:00:10.000 1 1 I TAG: old-k\n"
        b"01-02 10:00:11.000 1 1 I TAG: old-l\n"
        b"01-02 10:00:12.000 1 1 I TAG: old-m\n"
        b"01-02 10:00:13.000 1 1 I TAG: old-n\n"
        b"01-02 10:00:14.000 1 1 I TAG: old-o\n"
        b"01-02 10:00:15.000 1 1 I TAG: old-p\n"
        b"01-02 10:00:16.000 1 1 I TAG: old-q\n"
        b"01-02 10:00:17.000 1 1 I TAG: old-r\n"
        b"01-02 10:00:18.000 1 1 I TAG: old-s\n"
        b"01-02 10:00:19.000 1 1 I TAG: old-t\n"
    )
    if phase == "end":
        hilog += b"01-02 10:00:20.000 10 10 I FN01: req-1 complete\n"
    path = run_dir / f"raw/{phase}-hilog.txt"
    subject.write_bytes(path, hilog)
    return {
        "captured_at": "2026-07-28T00:00:00+00:00",
        "serial": SERIAL,
        "enforcing": mode,
        "boot_id": BOOT_ID,
        "uptime_seconds": uptime,
        "software_version": "OpenHarmony 6.1.0.31",
        "uname": "Linux d600",
        "files": {
            BRIDGE: {
                "sha256": EXPECTED,
                "selinux_label": "u:object_r:system_lib_file:s0",
            }
        },
        "processes": {"appspawn-x": [process()]},
        "hilog_relative_path": f"raw/{phase}-hilog.txt",
        "hilog_sha256": subject.sha256_bytes(hilog),
        "raw_sha256": {f"raw/{phase}-hilog.txt": subject.sha256_bytes(hilog)},
    }


def make_bundle(run_dir: Path, mode="Enforcing", receipt_start=101.0):
    begin = snapshot(run_dir, "begin", 100.0, mode=mode)
    end = snapshot(run_dir, "end", 110.0, mode=mode)
    session = {
        "schema_version": "1.0",
        "tool_version": subject.TOOL_VERSION,
        "session_id": "test-session",
        "action_id": "Fn01.A04",
        "serial": SERIAL,
        "expected_hashes": {BRIDGE: EXPECTED},
        "contract_inputs": {
            "definition": {"sha256": "d" * 64},
            "verification": {"sha256": "e" * 64},
            "implementation": {"sha256": "f" * 64},
        },
        "process_names": ["appspawn-x"],
        "device_start": begin,
    }
    request = run_dir / "raw/request.bin"
    response = run_dir / "raw/response.bin"
    subject.write_bytes(request, b'{"requestId":"req-1"}\n')
    subject.write_bytes(response, b'{"requestId":"req-1","status":"OK"}\n')
    receipt = {
        "schema_version": "1.0",
        "action_id": "Fn01.A04",
        "request_id": "req-1",
        "serial": SERIAL,
        "boot_id": BOOT_ID,
        "started_uptime_seconds": receipt_start,
        "finished_uptime_seconds": 109.0,
        "artifact_hashes": {BRIDGE: EXPECTED},
        "contract_sha256": {
            "definition": "d" * 64,
            "verification": "e" * 64,
            "implementation": "f" * 64,
        },
        "request_sha256": subject.sha256_file(request),
        "response_sha256": subject.sha256_file(response),
        "stored_request": "raw/request.bin",
        "stored_response": "raw/response.bin",
        "request_process": {
            "pid": 10,
            "uid": 0,
            "gid": 0,
            "name": "appspawn-x",
            "selinux_context": "u:r:appspawn:s0",
        },
    }
    return session, end, receipt


def add_body_digest(value):
    value["receipt_body_sha256"] = subject.sha256_bytes(
        subject.canonical_json_bytes(value)
    )
    return value


def reseal(value):
    value.pop("receipt_body_sha256", None)
    return add_body_digest(value)


def make_card1_bundle(
    bundle: Path,
    *,
    action_id="Fn01.A04",
    serial=SERIAL,
    boot_id=BOOT_ID,
):
    bundle.mkdir(parents=True)
    build = add_body_digest(
        {
            "schema_version": subject.CARD1_BUILD_SCHEMA,
            "action_id": action_id,
            "generation_id": f"{action_id}-fixture-generation",
            "generation_digest": "1" * 64,
            "captured_at": "2026-07-28T00:00:00+00:00",
            "target": {
                "os": "OpenHarmony",
                "version": "6.1.0.31",
                "arch": "AArch64",
            },
            "status": {
                "build_pass": True,
                "host_scope_build_pass": True,
                "target_scope_build_pass": True,
                "target_deployment_generation_bound": False,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "config": {"path": "fixture.json", "sha256": "2" * 64},
            "source_manifest": {"entries": [], "manifest_sha256": "3" * 64},
            "builder": {},
            "stages": [],
            "artifacts": [
                {
                    "role": "oh_adapter_bridge",
                    "kind": "elf",
                    "local_path": "out/bridge.so",
                    "device_path": BRIDGE,
                    "producer_stage": "target",
                    "sha256": EXPECTED,
                    "bytes": 123,
                }
            ],
            "semantics": {
                "build_pass_is_not_device_verified": True,
                "deployment_byte_match_is_not_action_behavior_verification": True,
            },
        }
    )
    build_path = bundle / "build-receipt.json"
    subject.write_json(build_path, build)
    device = add_body_digest(
        {
            "schema_version": subject.CARD1_DEVICE_SCHEMA,
            "action_id": action_id,
            "generation_id": build["generation_id"],
            "captured_at": "2026-07-28T00:01:00+00:00",
            "build_receipt": {
                "path": "/card1/original/build-receipt.json",
                "sha256": subject.sha256_file(build_path),
                "body_sha256": build["receipt_body_sha256"],
            },
            "collector": {
                "hdc_path": "/fixture/hdc",
                "hdc_sha256": "4" * 64,
                "hdc_version": "fixture",
            },
            "device": {
                "serial": serial,
                "boot_id_before": boot_id,
                "boot_id_after": boot_id,
                "os_version": "OpenHarmony 6.1.0.31",
                "security_mode": "Enforcing",
            },
            "deployed_artifacts": [
                {
                    "role": "oh_adapter_bridge",
                    "device_path": BRIDGE,
                    "sha256": EXPECTED,
                    "bytes": 123,
                }
            ],
            "status": {
                "read_only_capture_complete": True,
                "target_deployment_generation_bound": False,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "semantics": {
                "capture_performed_no_deployment": True,
                "deployment_byte_match_is_not_action_behavior_verification": True,
            },
        }
    )
    device_path = bundle / "device-receipt.json"
    subject.write_json(device_path, device)
    gate = add_body_digest(
        {
            "schema_version": subject.CARD1_GATE_SCHEMA,
            "action_id": action_id,
            "generation_id": build["generation_id"],
            "checked_at": "2026-07-28T00:02:00+00:00",
            "build_receipt": {
                "path": "/card1/original/build-receipt.json",
                "sha256": subject.sha256_file(build_path),
            },
            "device_receipt": {
                "path": "/card1/original/device-receipt.json",
                "sha256": subject.sha256_file(device_path),
            },
            "device_serial": serial,
            "gate_status": "PASS",
            "status": {
                "build_pass": True,
                "host_scope_build_pass": True,
                "target_scope_build_pass": True,
                "target_deployment_generation_bound": True,
                "device_verified": False,
                "formal_verdict": "NOT_ISSUED",
            },
            "failures": [],
            "semantics": {
                "pass_means_exact_deployed_bytes_for_same_generation": True,
                "pass_does_not_mean_action_behavior_device_verified": True,
                "independent_action_verifier_still_required": True,
            },
        }
    )
    gate_path = bundle / "gate-report.json"
    subject.write_json(gate_path, gate)
    subject.write_manifest(bundle)
    return {
        "build": build,
        "build_path": build_path,
        "device": device,
        "device_path": device_path,
        "gate": gate,
        "gate_path": gate_path,
        "manifest_path": bundle / "MANIFEST.sha256",
    }


def make_valid_begin_bundle(run_dir: Path, provenance_bundle: Path):
    card1 = make_card1_bundle(provenance_bundle)
    metadata, expected_hashes = subject.freeze_card1_provenance_bundle(
        run_dir,
        card1["manifest_path"],
        card1["gate_path"],
        expected_action_id="Fn01.A04",
        expected_serial=SERIAL,
    )
    begin = snapshot(run_dir, "begin", 100.0)
    session = {
        "schema_version": "1.0",
        "tool_version": subject.TOOL_VERSION,
        "session_id": "test-session",
        "action_id": "Fn01.A04",
        "serial": SERIAL,
        "original_serial": SERIAL,
        "allowed_serials": [SERIAL],
        "expected_hashes": expected_hashes,
        "provenance": metadata,
        "process_names": ["appspawn-x"],
        "device_start": begin,
    }
    subject.write_json(run_dir / "session.json", session)
    subject.write_json(
        run_dir / "validation.json",
        {
            "phase": "begin",
            "evidence_status": "DEVELOPER_EVIDENCE_VALID",
            "formal_verdict": "NOT_ISSUED",
            "reasons": [],
        },
    )
    subject.write_manifest(run_dir)
    return session


class EvidenceValidationTest(unittest.TestCase):
    def test_valid_bundle_is_developer_evidence_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            reasons, details = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertEqual([], reasons)
            self.assertTrue(details["hilog_window_valid"])
            result = subject.write_validation(
                run_dir, phase="test", reasons=reasons, details=details
            )
            self.assertEqual("DEVELOPER_EVIDENCE_VALID", result["evidence_status"])
            self.assertEqual("NOT_ISSUED", result["formal_verdict"])

    def test_permissive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir, mode="Permissive")
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertTrue(any(item.startswith("SELINUX_NOT_ENFORCING") for item in reasons))

    def test_artifact_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            end["files"][BRIDGE]["sha256"] = "c" * 64
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertTrue(
                any(item.startswith("ARTIFACT_HASH_MISMATCH") for item in reasons)
            )

    def test_stale_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir, receipt_start=90.0)
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("RECEIPT_STALE_BEFORE_CAPTURE", reasons)

    def test_rotated_unrelated_hilog_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            replacement = b"entirely unrelated log window\n"
            subject.write_bytes(run_dir / end["hilog_relative_path"], replacement)
            end["raw_sha256"][end["hilog_relative_path"]] = subject.sha256_bytes(
                replacement
            )
            reasons, details = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("HILOG_WINDOW_STALE_OR_ROTATED", reasons)
            self.assertFalse(details["hilog_window_valid"])

    def test_request_relevant_selinux_denial_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            end_path = run_dir / end["hilog_relative_path"]
            data = end_path.read_bytes() + (
                b"01-02 10:00:21.000 10 10 E audit: avc: denied req-1 appspawn-x\n"
            )
            subject.write_bytes(end_path, data)
            end["raw_sha256"][end["hilog_relative_path"]] = subject.sha256_bytes(data)
            reasons, details = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("REQUEST_RELEVANT_SELINUX_DENIAL", reasons)
            self.assertEqual(1, details["request_relevant_selinux_denial_count"])

    def test_5eab_is_hard_refused(self):
        with self.assertRaises(subject.EvidenceError):
            subject.ensure_safe_serial("5eab586000000000000000001123012c")

    def test_process_name_path_escape_is_refused(self):
        with self.assertRaises(subject.EvidenceError):
            subject.ensure_safe_process_names(["../../outside"])

    def test_receipt_member_traversal_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            receipt.write_text("{}\n")
            with self.assertRaises(subject.EvidenceError):
                subject.resolve_receipt_member(receipt, "../outside.json")

    def test_receipt_member_absolute_path_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = Path(temporary) / "receipt.json"
            receipt.write_text("{}\n")
            with self.assertRaises(subject.EvidenceError):
                subject.resolve_receipt_member(receipt, "/tmp/outside.json")

    def test_receipt_member_symlink_escape_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt_dir = root / "receipt"
            receipt_dir.mkdir()
            outside = root / "outside.json"
            outside.write_text("{}\n")
            (receipt_dir / "link.json").symlink_to(outside)
            (receipt_dir / "receipt.json").write_text("{}\n")
            with self.assertRaises(subject.EvidenceError):
                subject.resolve_receipt_member(
                    receipt_dir / "receipt.json", "link.json"
                )

    def test_manifest_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            subject.write_bytes(run_dir / "raw/fact.txt", b"original\n")
            subject.write_json(run_dir / "session.json", {"schema_version": "1.0"})
            subject.write_manifest(run_dir)
            subject.write_bytes(run_dir / "raw/fact.txt", b"tampered\n")
            reasons = subject.verify_manifest(run_dir)
            self.assertTrue(
                any(
                    item.startswith("BUNDLE_MANIFEST_INVALID:manifest hash mismatch")
                    for item in reasons
                )
            )

    def test_manifest_dotdot_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            outside = root / "outside.bin"
            outside.write_bytes(b"outside\n")
            digest = subject.sha256_file(outside)
            (bundle / "MANIFEST.sha256").write_text(
                f"{digest}  ../outside.bin\n", encoding="utf-8"
            )
            reasons = subject.verify_manifest(bundle)
            self.assertTrue(any("ordinary relative path" in item for item in reasons))

    def test_manifest_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            outside = root / "outside.bin"
            outside.write_bytes(b"outside\n")
            (bundle / "link.bin").symlink_to(outside)
            digest = subject.sha256_file(outside)
            (bundle / "MANIFEST.sha256").write_text(
                f"{digest}  link.bin\n", encoding="utf-8"
            )
            reasons = subject.verify_manifest(bundle)
            self.assertTrue(any("symlink" in item for item in reasons))

    def test_normalized_receipt_absolute_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            outside = root / "outside.json"
            outside.write_text('{"request_id":"req-1"}\n')
            receipt = {
                "request_id": "req-1",
                "stored_receipt": str(outside),
                "source_receipt_sha256": subject.sha256_file(outside),
            }
            reasons = subject.verify_normalized_receipt_integrity(bundle, receipt)
            self.assertTrue(
                any(item.startswith("RECEIPT_SOURCE_INVALID") for item in reasons)
            )

    def test_stored_request_absolute_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            session, end, receipt = make_bundle(run_dir)
            outside = root / "outside-request.bin"
            outside.write_bytes(b'{"requestId":"req-1"}\n')
            receipt["stored_request"] = str(outside)
            receipt["request_sha256"] = subject.sha256_file(outside)
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertTrue(
                any(
                    item.startswith("STORED_REQUEST_RESPONSE_INVALID")
                    for item in reasons
                )
            )

    def test_card1_closed_bundle_derives_expected_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1")
            metadata, expected, _, _ = subject.load_card1_provenance_bundle(
                card1["manifest_path"],
                card1["gate_path"],
                expected_action_id="Fn01.A04",
                expected_serial=SERIAL,
            )
            self.assertEqual({BRIDGE: EXPECTED}, expected)
            self.assertEqual(
                subject.CARD1_ADAPTER_SCHEMA, metadata["adapter_schema"]
            )
            self.assertFalse(metadata["device_verified"])

    def test_begin_imports_hashes_only_from_card1_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1")
            run_dir = root / "run"
            args = argparse.Namespace(
                action_id="Fn01.A04",
                serial=SERIAL,
                out_dir=str(run_dir),
                provenance_manifest=str(card1["manifest_path"]),
                provenance_receipt=str(card1["gate_path"]),
                root=str(Path(__file__).resolve().parents[4]),
                file_label_path=[],
                process=["appspawn-x"],
                hdc="/fixture/hdc",
            )

            def fake_capture(**kwargs):
                return snapshot(kwargs["raw_dir"].parent, kwargs["phase"], 100.0)

            with mock.patch.object(
                subject, "capture_snapshot", side_effect=fake_capture
            ) as capture:
                self.assertEqual(0, subject.command_begin(args))
                capture.assert_called_once()
            session = json.loads((run_dir / "session.json").read_text())
            self.assertEqual({BRIDGE: EXPECTED}, session["expected_hashes"])
            self.assertEqual([SERIAL], session["allowed_serials"])
            self.assertEqual([], subject.verify_manifest(run_dir))

    def test_card1_unknown_build_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1")
            build = copy.deepcopy(card1["build"])
            build["unknown"] = "not-admitted"
            reseal(build)
            subject.write_json(card1["build_path"], build)
            device = copy.deepcopy(card1["device"])
            device["build_receipt"]["sha256"] = subject.sha256_file(
                card1["build_path"]
            )
            device["build_receipt"]["body_sha256"] = build["receipt_body_sha256"]
            reseal(device)
            subject.write_json(card1["device_path"], device)
            gate = copy.deepcopy(card1["gate"])
            gate["build_receipt"]["sha256"] = subject.sha256_file(
                card1["build_path"]
            )
            gate["device_receipt"]["sha256"] = subject.sha256_file(
                card1["device_path"]
            )
            reseal(gate)
            subject.write_json(card1["gate_path"], gate)
            subject.write_manifest(root / "card1")
            with self.assertRaisesRegex(subject.EvidenceError, "unsupported fields"):
                subject.load_card1_provenance_bundle(
                    card1["manifest_path"],
                    card1["gate_path"],
                    expected_action_id="Fn01.A04",
                    expected_serial=SERIAL,
                )

    def test_card1_gate_not_pass_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1")
            gate = copy.deepcopy(card1["gate"])
            gate["gate_status"] = "FAIL"
            gate["status"]["target_deployment_generation_bound"] = False
            gate["failures"] = [{"code": "fixture", "detail": "fixture"}]
            reseal(gate)
            subject.write_json(card1["gate_path"], gate)
            subject.write_manifest(root / "card1")
            with self.assertRaisesRegex(subject.EvidenceError, "not PASS"):
                subject.load_card1_provenance_bundle(
                    card1["manifest_path"],
                    card1["gate_path"],
                    expected_action_id="Fn01.A04",
                    expected_serial=SERIAL,
                )

    def test_card1_cross_action_coverage_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1", action_id="Fn01.A04")
            with self.assertRaisesRegex(subject.EvidenceError, "cross-Action coverage"):
                subject.load_card1_provenance_bundle(
                    card1["manifest_path"],
                    card1["gate_path"],
                    expected_action_id="Fn01.A01",
                    expected_serial=SERIAL,
                )

    def test_card1_manifest_extra_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            card1 = make_card1_bundle(root / "card1")
            (root / "card1/unlisted.txt").write_text("unlisted\n")
            with self.assertRaisesRegex(subject.EvidenceError, "closure mismatch"):
                subject.load_card1_provenance_bundle(
                    card1["manifest_path"],
                    card1["gate_path"],
                    expected_action_id="Fn01.A04",
                    expected_serial=SERIAL,
                )

    def test_request_process_only_in_end_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            rogue = process(pid=99)
            rogue.update(
                {
                    "name": "rogue-service",
                    "args": "rogue-service",
                    "exe": "/system/bin/rogue-service",
                    "selinux_context": "u:r:rogue:s0",
                }
            )
            end["processes"]["rogue-service"] = [rogue]
            receipt["request_process"] = {
                key: rogue[key]
                for key in ("pid", "uid", "gid", "name", "selinux_context")
            }
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("REQUEST_PROCESS_NOT_IN_BEGIN_WHITELIST", reasons)

    def test_request_process_cmdline_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            end["processes"]["appspawn-x"][0]["cmdline_sha256"] = "c" * 64
            reasons, _ = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("PROCESS_IDENTITY_CHANGED:appspawn-x", reasons)
            self.assertIn("REQUEST_PROCESS_IDENTITY_CHANGED", reasons)

    def test_unattributed_denial_in_request_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            session, end, receipt = make_bundle(run_dir)
            end_path = run_dir / end["hilog_relative_path"]
            data = end_path.read_bytes() + (
                b'01-02 10:00:21.000 55 55 E audit: avc: denied '
                b'pid=777 comm="unrelated" scontext=u:r:other:s0\n'
            )
            subject.write_bytes(end_path, data)
            end["raw_sha256"][end["hilog_relative_path"]] = subject.sha256_bytes(data)
            reasons, details = subject.validate_receipt_and_end(
                run_dir=run_dir,
                session=session,
                end_snapshot=end,
                receipt=receipt,
            )
            self.assertIn("UNATTRIBUTED_SELINUX_DENIAL_IN_REQUEST_WINDOW", reasons)
            self.assertEqual(1, details["unattributed_selinux_denial_count"])

    def test_finalize_checks_manifest_before_any_hdc(self):
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            subject.write_json(run_dir / "session.json", {"serial": SERIAL})
            subject.write_bytes(
                run_dir / "MANIFEST.sha256",
                ("0" * 64 + "  session.json\n").encode(),
            )
            args = argparse.Namespace(
                run_dir=str(run_dir),
                request_receipt=str(run_dir / "missing.json"),
                hdc="/fixture/hdc",
            )
            with mock.patch.object(subject, "capture_snapshot") as capture:
                with self.assertRaisesRegex(subject.EvidenceError, "pre-HDC"):
                    subject.command_finalize(args)
                capture.assert_not_called()

    def test_finalize_rejects_serial_lock_change_before_any_hdc(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / "run"
            run_dir.mkdir()
            session = make_valid_begin_bundle(run_dir, root / "card1")
            session["serial"] = "654b3a6b00000000000000000824012c"
            subject.write_json(run_dir / "session.json", session)
            subject.write_manifest(run_dir)
            args = argparse.Namespace(
                run_dir=str(run_dir),
                request_receipt=str(run_dir / "missing.json"),
                hdc="/fixture/hdc",
            )
            with mock.patch.object(subject, "capture_snapshot") as capture:
                with self.assertRaisesRegex(subject.EvidenceError, "serial is not locked"):
                    subject.command_finalize(args)
                capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
