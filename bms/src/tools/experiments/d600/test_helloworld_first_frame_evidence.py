#!/usr/bin/env python3
"""Fail-closed tests for the HelloWorld first-frame evidence-pack verifier."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import helloworld_first_frame_contract as contract
import verify_helloworld_first_frame_evidence as verifier


SHA_1 = "1" * 64
SHA_2 = "2" * 64
SERIAL = "fixture-d600"
BOOT_ID = "3b219a52-cc25-4afb-8854-0a96bf091b68"
GENERATION_ID = "5" * 64
PID = 4321
PPID = 1200
START_TICKS = 9988


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _proc_stat(pid: int, ppid: int, start_ticks: int) -> str:
    # Fields 3..22: state, ppid, then enough stable placeholders for starttime.
    return f"{pid} (com.example.hel) S {ppid} " + " ".join(["0"] * 17) + f" {start_ticks}\n"


class EvidencePackFixture:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw = root / "candidate/raw/candidate-001"
        self.raw.mkdir(parents=True)
        self.first = self.raw / "first-frame.png"
        self.hold = self.raw / "hold-end.png"
        self.precondition = self.raw / "precondition.png"
        for path in (self.first, self.hold):
            image = Image.new("RGB", (48, 48), "white")
            ImageDraw.Draw(image).rectangle((8, 18, 40, 30), fill="black")
            image.save(path)
        precondition = Image.new("RGB", (48, 48), "navy")
        ImageDraw.Draw(precondition).rectangle((0, 0, 8, 8), fill="white")
        precondition.save(self.precondition)
        (self.raw / "first-frame-proc-stat.txt").write_text(
            _proc_stat(PID, PPID, START_TICKS), encoding="utf-8"
        )
        (self.raw / "hold-end-proc-stat.txt").write_text(
            _proc_stat(PID, PPID, START_TICKS), encoding="utf-8"
        )
        (self.raw / "pre-existing-processes.txt").write_text("", encoding="utf-8")
        (self.raw / "hold-end-proc-maps.txt").write_text(
            "700000-701000 r-xp 000000 00:00 0 /system/android/lib64/libart.so\n",
            encoding="utf-8",
        )
        self.candidate = self._candidate()
        self.device_generation = self._device_generation()
        self.content_review = self._content_review()
        self.verdict = self._verdict()
        self.write()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _candidate(self) -> dict[str, object]:
        return {
            "candidate_id": "candidate-001",
            "run_id": "fixture-run-001",
            "apk": {
                "sha256": contract.HELLOWORLD_APK_SHA256,
                "package_name": contract.HELLOWORLD_PACKAGE,
                "activity_name": contract.HELLOWORLD_ACTIVITY,
                "unmodified": True,
            },
            "device": {
                "serial": SERIAL,
                "boot_id": BOOT_ID,
                "oh_version": "OpenHarmony-6.1.0.31",
                "selinux": "Permissive",
                "lease_ref": "fixture-lease",
            },
            "generation": {
                "generation_id": GENERATION_ID,
                "device_readback_receipt": "device-generation.json",
                "identity_valid": True,
            },
            "change_set_ref": "change-set.json",
            "launch": {
                "cold_precondition": True,
                "started_at_utc": "2026-08-04T12:00:00Z",
                "started_at_monotonic": 100.0,
                "request_id": "request-001",
            },
            "process": {
                "pid": PID,
                "start_ticks": START_TICKS,
                "parent_pid": PPID,
                "package_bound": True,
                "alive_at_hold_end": True,
            },
            "observations": {
                "on_resume": True,
                "app_window_visible": True,
                "present_observed": True,
                "hello_world_visible": True,
                "first_frame_seconds": 3.0,
                "hold_seconds": 6.0,
                "screens": [
                    {
                        "role": "PRECONDITION",
                        "path": self.rel(self.precondition),
                        "sha256": _sha256(self.precondition),
                        "captured_at_utc": "2026-08-04T11:59:58Z",
                    },
                    {
                        "role": "FIRST_FRAME",
                        "path": self.rel(self.first),
                        "sha256": _sha256(self.first),
                        "captured_at_utc": "2026-08-04T12:00:03Z",
                    },
                    {
                        "role": "HOLD_END",
                        "path": self.rel(self.hold),
                        "sha256": _sha256(self.hold),
                        "captured_at_utc": "2026-08-04T12:00:09Z",
                    },
                ],
            },
            "pnf": {"positive": "PASS", "negative": "PASS", "failure": "PASS"},
            "first_bad": "NONE",
            "terminal_state": "DEVELOPER_OBSERVED_FIRST_FRAME",
            "evidence_manifest_sha256": SHA_1,
        }

    def _device_generation(self) -> dict[str, object]:
        return {
            "serial": SERIAL,
            "boot_id": BOOT_ID,
            "generation_id": GENERATION_ID,
            "apk_sha256": contract.HELLOWORLD_APK_SHA256,
            "device_readback_sha256": SHA_2,
            "oh_version": "OpenHarmony-6.1.0.31",
            "selinux": "Permissive",
            "appspawn_parent": {
                "pid": PPID,
                "ppid": 1,
                "start_ticks": 123,
                "exe": "/system/bin/appspawn-x",
            },
            "artifacts": {
                "installed_apk": {
                    "path": "/data/app/el1/bundle/public/com.example.helloworld/android/base.apk",
                    "sha256": contract.HELLOWORLD_APK_SHA256,
                },
                "child_maps": {
                    "path": self.rel(self.raw / "hold-end-proc-maps.txt"),
                    "sha256": _sha256(self.raw / "hold-end-proc-maps.txt"),
                },
            },
        }

    def _content_review(self) -> dict[str, object]:
        return {
            "schema_version": "bridge.p0.helloworld-content-review.v1",
            "candidate_ref": "candidate.json",
            "reviewer_role": "implementation-agent-visual-review",
            "precondition": {
                "old_process_count": 0,
                "screen": "HOME without Android application content",
                "sha256": _sha256(self.precondition),
            },
            "first_frame": {
                "monotonic": 103.0,
                "seconds_after_launch": 3.0,
                "visible_text": ["Hello World!"],
                "nonblack_ratio": 1.0,
                "luminance_span": 255,
                "sha256": _sha256(self.first),
            },
            "hold_end": {
                "monotonic": 109.0,
                "seconds_after_first_frame": 6.0,
                "expected_text_still_visible": True,
                "same_pixels_sha256": True,
                "same_process": {"pid": PID, "start_ticks": START_TICKS, "parent_pid": PPID},
                "sha256": _sha256(self.hold),
            },
            "window_binding": {
                "mission_id": 1,
                "ability_state": "FOREGROUND",
                "native_window_log": "candidate/raw/candidate-001/hilog.txt:1",
                "egl_surface_non_null": True,
            },
            "decision": "EXPECTED_HELLOWORLD_CONTENT_VISIBLE_AND_STABLE",
            "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
            "formal_journey_verdict": contract.FORMAL_VERDICT,
        }

    def _verdict(self) -> dict[str, object]:
        return {
            "candidate_ref": "candidate/candidate.json",
            "evidence_manifest_sha256": SHA_1,
            "verdict": "DEVELOPER_OBSERVED_FIRST_FRAME",
            "first_bad": "NONE",
            "issued_by": "implementation-agent",
            "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
            "formal_journey_verdict": contract.FORMAL_VERDICT,
        }

    def write(self) -> None:
        _json(self.root / "candidate/candidate.json", self.candidate)
        _json(self.root / "candidate/content-review.json", self.content_review)
        _json(self.root / "device-generation.json", self.device_generation)
        _json(self.root / "DEVELOPER-VERDICT.json", self.verdict)
        manifest_paths = sorted(
            [
                self.precondition,
                self.first,
                self.hold,
                self.raw / "first-frame-proc-stat.txt",
                self.raw / "hold-end-proc-stat.txt",
                self.raw / "pre-existing-processes.txt",
                self.raw / "hold-end-proc-maps.txt",
            ],
            key=lambda path: self.rel(path),
        )
        manifest = "".join(f"{_sha256(path)}  {self.rel(path)}\n" for path in manifest_paths)
        manifest_path = self.root / "evidence-manifest.sha256"
        manifest_path.write_text(manifest, encoding="utf-8")
        manifest_sha = _sha256(manifest_path)
        self.candidate["evidence_manifest_sha256"] = manifest_sha
        self.verdict["evidence_manifest_sha256"] = manifest_sha
        _json(self.root / "candidate/candidate.json", self.candidate)
        _json(self.root / "DEVELOPER-VERDICT.json", self.verdict)


class HelloWorldEvidenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pack = EvidencePackFixture(Path(self.temp.name))

    def verify(self, **overrides: str) -> verifier.VerificationResult:
        expectations = verifier.ExpectedIdentity(
            apk_sha256=overrides.get("apk_sha256", contract.HELLOWORLD_APK_SHA256),
            serial=overrides.get("serial", SERIAL),
            boot_id=overrides.get("boot_id", BOOT_ID),
            generation_id=overrides.get("generation_id", GENERATION_ID),
        )
        return verifier.verify_evidence_pack(self.pack.root, expectations=expectations)

    def assert_rejected(self, result: verifier.VerificationResult, path: str) -> None:
        self.assertEqual(result.verdict, "REJECTED", result.to_dict())
        self.assertTrue(any(error.path == path for error in result.errors), result.to_dict())

    def test_accepts_complete_success_pack(self) -> None:
        result = self.verify()
        self.assertEqual(result.verdict, "ACCEPTED_DEVELOPER_OBSERVATION", result.to_dict())
        self.assertEqual(result.errors, ())

    def test_accepts_typed_failure_without_optional_device_artifacts(self) -> None:
        self.pack.candidate["process"] = {
            "pid": None,
            "start_ticks": None,
            "parent_pid": None,
            "package_bound": False,
            "alive_at_hold_end": False,
        }
        self.pack.candidate["observations"] = {
            "on_resume": False,
            "app_window_visible": False,
            "present_observed": False,
            "hello_world_visible": False,
            "first_frame_seconds": None,
            "hold_seconds": 0.0,
            "screens": [],
        }
        self.pack.candidate["first_bad"] = "ABILITY_COMPONENT_NOT_INSTALLED"
        self.pack.candidate["terminal_state"] = "FAIL_LAUNCH"
        self.pack.device_generation.pop("appspawn_parent")
        self.pack.device_generation.pop("artifacts")
        self.pack.verdict["verdict"] = "FAIL_LAUNCH"
        self.pack.verdict["first_bad"] = "ABILITY_COMPONENT_NOT_INSTALLED"
        self.pack.write()

        result = self.verify()
        self.assertEqual(result.verdict, "ACCEPTED_TYPED_FAILURE", result.to_dict())
        self.assertEqual(result.errors, ())

    def test_rejects_wrong_apk(self) -> None:
        self.pack.candidate["apk"]["sha256"] = "f" * 64
        self.pack.write()
        self.assert_rejected(self.verify(), "candidate.apk.sha256")

    def test_rejects_wrong_serial_boot_or_generation(self) -> None:
        cases = (
            ("serial", "other-d600", "candidate.device.serial"),
            ("boot_id", "6c6b63f9-850c-4f5a-9af3-d28370a47732", "candidate.device.boot_id"),
            ("generation_id", "9" * 64, "candidate.generation.generation_id"),
        )
        for field, value, path in cases:
            with self.subTest(field=field):
                self.assert_rejected(self.verify(**{field: value}), path)

    def test_rejects_old_pid_start_ticks(self) -> None:
        self.pack.candidate["process"]["start_ticks"] = START_TICKS - 1
        self.pack.content_review["hold_end"]["same_process"]["start_ticks"] = START_TICKS - 1
        self.pack.write()
        self.assert_rejected(self.verify(), "candidate.process.start_ticks")

    def test_rejects_old_screenshot_timeline(self) -> None:
        screens = self.pack.candidate["observations"]["screens"]
        screens[1]["captured_at_utc"] = "2026-08-04T11:59:30Z"
        self.pack.write()
        self.assert_rejected(
            self.verify(), "candidate.observations.screens[FIRST_FRAME].captured_at_utc"
        )

    def test_rejects_non_hello_nonblack_image(self) -> None:
        Image.new("RGB", (48, 48), "orange").save(self.pack.first)
        Image.new("RGB", (48, 48), "orange").save(self.pack.hold)
        new_sha = _sha256(self.pack.first)
        for screen in self.pack.candidate["observations"]["screens"]:
            if screen["role"] in {"FIRST_FRAME", "HOLD_END"}:
                screen["sha256"] = new_sha
        self.pack.content_review["first_frame"]["sha256"] = new_sha
        self.pack.content_review["first_frame"]["visible_text"] = ["Settings"]
        self.pack.content_review["hold_end"]["sha256"] = new_sha
        self.pack.write()
        self.assert_rejected(self.verify(), "content_review.first_frame.visible_text")

    def test_rejects_missing_five_second_hold(self) -> None:
        self.pack.candidate["observations"]["hold_seconds"] = 4.9
        self.pack.content_review["hold_end"]["seconds_after_first_frame"] = 4.9
        self.pack.write()
        self.assert_rejected(self.verify(), "candidate.observations.hold_seconds")

    def test_rejects_developer_faking_formal_pass(self) -> None:
        self.pack.verdict["formal_journey_verdict"] = "PASS"
        self.pack.write()
        self.assert_rejected(self.verify(), "developer_verdict.formal_journey_verdict")

    def test_rejects_manifest_tamper_with_explicit_path(self) -> None:
        self.pack.first.write_bytes(b"tampered")
        self.assert_rejected(
            self.verify(),
            "evidence_manifest.candidate/raw/candidate-001/first-frame.png.sha256",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
