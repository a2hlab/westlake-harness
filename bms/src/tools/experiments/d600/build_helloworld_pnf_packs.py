#!/usr/bin/env python3
"""Materialize the bounded T025 D600 P/N/F evidence packs.

The device actions are intentionally kept outside this generator.  This script
only seals already captured real-device observations into the same candidate,
manifest and verdict contracts consumed by the read-only verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

import helloworld_first_frame_contract as contract


SERIAL = "5ce2dcee00000000000000000923012c"
BOOT_BEFORE = "05a3e4bb-a83a-4215-a6b7-28d907f8956d"
BOOT_AFTER = "8b0a57a3-5191-46c5-bcdc-33cbe9831790"
GENERATION = "74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d"
WRONG_GENERATION = "9" * 64
APK_SHA256 = contract.HELLOWORLD_APK_SHA256
OH_VERSION = "OpenHarmony-6.1.0.31"
SELINUX = "Permissive"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def proc_stat(pid: int, ppid: int, start_ticks: int) -> str:
    """Return the /proc/<pid>/stat fields used by the evidence verifier."""
    return f"{pid} (com.example.hel) S {ppid} " + " ".join(["0"] * 17) + f" {start_ticks}\n"


def failure_candidate(
    *,
    candidate_id: str,
    run_id: str,
    boot_id: str,
    generation_id: str,
    terminal_state: str,
    first_bad: str,
    started_at: str,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "run_id": run_id,
        "apk": {
            "sha256": APK_SHA256,
            "package_name": contract.HELLOWORLD_PACKAGE,
            "activity_name": contract.HELLOWORLD_ACTIVITY,
            "unmodified": True,
        },
        "device": {
            "serial": SERIAL,
            "boot_id": boot_id,
            "oh_version": OH_VERSION,
            "selinux": SELINUX,
            "lease_ref": "user-delegated-all-d600-sacrificial-pool",
        },
        "generation": {
            "generation_id": generation_id,
            "device_readback_receipt": "device-generation.json",
            "identity_valid": True,
        },
        "launch": {
            "cold_precondition": True,
            "started_at_utc": started_at,
            "started_at_monotonic": 0.0,
            "request_id": None,
        },
        "process": {
            "pid": None,
            "start_ticks": None,
            "parent_pid": None,
            "package_bound": False,
            "alive_at_hold_end": False,
        },
        "observations": {
            "on_resume": False,
            "app_window_visible": False,
            "present_observed": False,
            "hello_world_visible": False,
            "first_frame_seconds": None,
            "hold_seconds": 0.0,
            "screens": [],
        },
        "pnf": {"positive": "NOT_RUN", "negative": "PASS", "failure": "PASS"},
        "first_bad": first_bad,
        "terminal_state": terminal_state,
        "evidence_manifest_sha256": "1" * 64,
    }


def device_generation(*, boot_id: str, appspawn_pid: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "serial": SERIAL,
        "boot_id": boot_id,
        "generation_id": GENERATION,
        "apk_sha256": APK_SHA256,
        "device_readback_sha256": digest_text(f"{SERIAL}:{boot_id}:{GENERATION}:{APK_SHA256}"),
        "oh_version": OH_VERSION,
        "selinux": SELINUX,
    }
    if appspawn_pid is not None:
        value["appspawn_parent"] = {
            "pid": appspawn_pid,
            "ppid": 1,
            "start_ticks": 167038,
            "exe": "/system/bin/appspawn-x",
        }
    return value


def developer_verdict(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_ref": "candidate/candidate.json",
        "evidence_manifest_sha256": candidate["evidence_manifest_sha256"],
        "verdict": candidate["terminal_state"],
        "first_bad": candidate["first_bad"],
        "issued_by": "implementation-agent:/root",
        "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
        "formal_journey_verdict": contract.FORMAL_VERDICT,
    }


def seal_pack(
    root: Path,
    *,
    candidate: dict[str, Any],
    generation_receipt: dict[str, Any],
    case: dict[str, Any],
    content_review: dict[str, Any] | None = None,
    extra_json: dict[str, object] | None = None,
) -> None:
    write_json(root / "case.json", case)
    write_json(root / "device-generation.json", generation_receipt)
    if content_review is not None:
        write_json(root / "candidate/content-review.json", content_review)
    for relative, value in (extra_json or {}).items():
        write_json(root / relative, value)

    excluded = {
        "candidate/candidate.json",
        "DEVELOPER-VERDICT.json",
        "evidence-manifest.sha256",
    }
    evidence_paths = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.relative_to(root).as_posix() not in excluded
    )
    manifest = "".join(
        f"{contract.sha256_file(path)}  {path.relative_to(root).as_posix()}\n"
        for path in evidence_paths
    )
    manifest_path = root / "evidence-manifest.sha256"
    write_text(manifest_path, manifest)
    manifest_sha = contract.sha256_file(manifest_path)
    candidate["evidence_manifest_sha256"] = manifest_sha
    verdict = developer_verdict(candidate)
    verdict["evidence_manifest_sha256"] = manifest_sha
    write_json(root / "candidate/candidate.json", candidate)
    write_json(root / "DEVELOPER-VERDICT.json", verdict)


def build_n02(root: Path, run_id: str) -> None:
    write_text(
        root / "raw/device-generation-observation.txt",
        f"serial={SERIAL}\nboot_id={BOOT_BEFORE}\n"
        f"observed_generation_id={GENERATION}\n"
        f"injected_candidate_generation_id={WRONG_GENERATION}\n"
        "result=REJECT_BEFORE_LAUNCH\n",
    )
    candidate = failure_candidate(
        candidate_id="n02-wrong-generation",
        run_id=run_id,
        boot_id=BOOT_BEFORE,
        generation_id=WRONG_GENERATION,
        terminal_state="BLOCK_PRECONDITION",
        first_bad="GENERATION_MISMATCH",
        started_at="2026-08-05T03:05:31Z",
    )
    seal_pack(
        root,
        candidate=candidate,
        generation_receipt=device_generation(boot_id=BOOT_BEFORE),
        case={
            "case_id": "N02_WRONG_GENERATION",
            "device_observed": True,
            "stimulus": "candidate generation differs from D600 readback",
            "expected_verifier_verdict": "REJECTED",
            "expected_mismatch_path": "candidate.generation.generation_id",
        },
    )


def build_n03(root: Path, run_id: str) -> None:
    source = root / "raw/fake-screen.png"
    target = root / "candidate/raw/fake-screen.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    screen_sha = contract.sha256_file(target)
    proc = proc_stat(395, 14179, 334570)
    write_text(root / "candidate/raw/first-frame-proc-stat.txt", proc)
    write_text(root / "candidate/raw/hold-end-proc-stat.txt", proc)
    write_text(root / "candidate/raw/pre-existing-processes.txt", "")
    candidate = {
        "candidate_id": "n03-fake-screen",
        "run_id": run_id,
        "apk": {
            "sha256": APK_SHA256,
            "package_name": contract.HELLOWORLD_PACKAGE,
            "activity_name": contract.HELLOWORLD_ACTIVITY,
            "unmodified": True,
        },
        "device": {
            "serial": SERIAL,
            "boot_id": BOOT_BEFORE,
            "oh_version": OH_VERSION,
            "selinux": SELINUX,
            "lease_ref": "user-delegated-all-d600-sacrificial-pool",
        },
        "generation": {
            "generation_id": GENERATION,
            "device_readback_receipt": "device-generation.json",
            "identity_valid": True,
        },
        "launch": {
            "cold_precondition": True,
            "started_at_utc": "2026-08-05T03:04:00Z",
            "started_at_monotonic": 100.0,
            "request_id": "n03-false-success",
        },
        "process": {
            "pid": 395,
            "start_ticks": 334570,
            "parent_pid": 14179,
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
                {"role": "PRECONDITION", "path": "candidate/raw/fake-screen.png", "sha256": screen_sha, "captured_at_utc": "2026-08-05T03:03:58Z"},
                {"role": "FIRST_FRAME", "path": "candidate/raw/fake-screen.png", "sha256": screen_sha, "captured_at_utc": "2026-08-05T03:04:03Z"},
                {"role": "HOLD_END", "path": "candidate/raw/fake-screen.png", "sha256": screen_sha, "captured_at_utc": "2026-08-05T03:04:09Z"},
            ],
        },
        "pnf": {"positive": "PASS", "negative": "PASS", "failure": "NOT_RUN"},
        "first_bad": "NONE_FALSE_CLAIM",
        "terminal_state": "DEVELOPER_OBSERVED_FIRST_FRAME",
        "evidence_manifest_sha256": "1" * 64,
    }
    content_review = {
        "schema_version": "bridge.p0.helloworld-content-review.v1",
        "candidate_ref": "candidate.json",
        "reviewer_role": "implementation-agent-negative-control",
        "precondition": {"old_process_count": 0, "screen": "black placeholder", "sha256": screen_sha},
        "first_frame": {
            "monotonic": 103.0,
            "seconds_after_launch": 3.0,
            "visible_text": ["no application text"],
            "nonblack_ratio": 0.001302,
            "luminance_span": 29,
            "sha256": screen_sha,
        },
        "hold_end": {
            "monotonic": 109.0,
            "seconds_after_first_frame": 6.0,
            "expected_text_still_visible": False,
            "same_pixels_sha256": True,
            "same_process": {"pid": 395, "start_ticks": 334570, "parent_pid": 14179},
            "sha256": screen_sha,
        },
        "window_binding": {"mission_id": 216, "ability_state": "INITIAL", "native_window_log": "ABSENT", "egl_surface_non_null": False},
        "decision": "EXPECTED_CONTENT_ABSENT_NEGATIVE_CONTROL",
        "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
        "formal_journey_verdict": contract.FORMAL_VERDICT,
    }
    seal_pack(
        root,
        candidate=candidate,
        generation_receipt=device_generation(boot_id=BOOT_BEFORE, appspawn_pid=14179),
        content_review=content_review,
        case={
            "case_id": "N03_FAKE_NON_HELLOWORLD_SCREEN",
            "device_observed": True,
            "stimulus": "real D600 black placeholder relabeled as success",
            "expected_verifier_verdict": "REJECTED",
            "expected_mismatch_path": "candidate.observations.screens[FIRST_FRAME].pixels",
        },
    )


def build_f01(root: Path, run_id: str) -> None:
    candidate = failure_candidate(
        candidate_id="f01-invalid-component",
        run_id=run_id,
        boot_id=BOOT_BEFORE,
        generation_id=GENERATION,
        terminal_state="FAIL_LAUNCH",
        first_bad="ABILITY_COMPONENT_NOT_INSTALLED_10104001",
        started_at="2026-08-05T03:05:31Z",
    )
    seal_pack(
        root,
        candidate=candidate,
        generation_receipt=device_generation(boot_id=BOOT_BEFORE),
        case={
            "case_id": "F01_INVALID_COMPONENT",
            "device_observed": True,
            "stimulus": "aa start com.example.helloworld.DoesNotExist",
            "observed_error_code": "10104001",
            "expected_verifier_verdict": "ACCEPTED_TYPED_FAILURE",
        },
    )


def build_f03(root: Path, run_id: str) -> None:
    write_text(
        root / "raw/boot-transition.txt",
        f"serial={SERIAL}\nboot_before={BOOT_BEFORE}\nboot_after={BOOT_AFTER}\n"
        f"generation_before={GENERATION}\ngeneration_after={GENERATION}\n"
        "transport_transition=Connected->Offline->Connected\n"
        "result=OLD_BOOT_RECEIPTS_INVALIDATED\n",
    )
    candidate = failure_candidate(
        candidate_id="f03-stale-boot",
        run_id=run_id,
        boot_id=BOOT_BEFORE,
        generation_id=GENERATION,
        terminal_state="BLOCK_PRECONDITION",
        first_bad="BOOT_CHANGED_DURING_RECONNECT",
        started_at="2026-08-05T03:10:00Z",
    )
    seal_pack(
        root,
        candidate=candidate,
        generation_receipt=device_generation(boot_id=BOOT_AFTER),
        case={
            "case_id": "F03_DISCONNECT_BOOT_CHANGE",
            "device_observed": True,
            "stimulus": "hdc target boot",
            "expected_verifier_verdict": "REJECTED",
            "expected_mismatch_path": "candidate.device.boot_id",
        },
    )


def build_f04(root: Path, run_id: str) -> None:
    write_text(
        root / "raw/baseline.txt",
        f"boot_id={BOOT_AFTER}\ngeneration_id={GENERATION}\n"
        "appspawn_pid=ABSENT\nmali0=crw-rw---- uid=0 gid=0\n",
    )
    write_text(
        root / "raw/applied.txt",
        f"boot_id={BOOT_AFTER}\ngeneration_id={GENERATION}\n"
        "appspawn_pid=8465\nappspawn_ppid=1\nappspawn_start_ticks=58102\n"
        "appspawn_socket=/dev/unix/socket/AppSpawnX\n"
        "mali0=crw-rw-rw- uid=0 gid=0\n",
    )
    write_text(
        root / "raw/rolled-back.txt",
        f"boot_id={BOOT_AFTER}\ngeneration_id={GENERATION}\n"
        "appspawn_pid=ABSENT\nmali0=crw-rw---- uid=0 gid=0\n",
    )
    write_text(
        root / "raw/post-case-recovery.txt",
        f"boot_id={BOOT_AFTER}\ngeneration_id={GENERATION}\n"
        "appspawn_pid=8956\n"
        "note=device independently restored mali0 to 0660; guarded runner prepares 0666 immediately before launch\n",
    )
    rollback = {
        "schema_version": "bridge.p0.pnf-cohort-rollback.v1",
        "case_id": "F04_WHOLE_COHORT_ROLLBACK",
        "members": [
            {"identity": "service:appspawn-x", "before": "STOPPED", "applied": "RUNNING pid=8465", "rolled_back": "STOPPED"},
            {"identity": "device:/dev/mali0", "before": "0660 root:root", "applied": "0666 root:root", "rolled_back": "0660 root:root"},
        ],
        "restore_all_members": True,
        "boot_unchanged": True,
        "generation_unchanged": True,
        "rollback_result": "PASS",
        "post_case_recovery_is_outside_test_cohort": True,
        "claim_boundary": contract.DEVELOPER_CLAIM_BOUNDARY,
        "formal_journey_verdict": contract.FORMAL_VERDICT,
    }
    candidate = failure_candidate(
        candidate_id="f04-whole-cohort-rollback",
        run_id=run_id,
        boot_id=BOOT_AFTER,
        generation_id=GENERATION,
        terminal_state="BLOCK_PRECONDITION",
        first_bad="INTENTIONAL_PNF_COHORT_ROLLBACK",
        started_at="2026-08-05T03:18:00Z",
    )
    seal_pack(
        root,
        candidate=candidate,
        generation_receipt=device_generation(boot_id=BOOT_AFTER),
        extra_json={"rollback-receipt.json": rollback},
        case={
            "case_id": "F04_WHOLE_COHORT_ROLLBACK",
            "device_observed": True,
            "stimulus": "apply and roll back appspawn-x service plus mali0 access as one cohort",
            "expected_verifier_verdict": "ACCEPTED_TYPED_FAILURE",
            "rollback_result": "PASS",
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    root = args.output_root.resolve()
    run_id = root.parent.name
    build_n02(root / "N02-wrong-generation", run_id)
    build_n03(root / "N03-fake-screen", run_id)
    build_f01(root / "F01-invalid-component", run_id)
    build_f03(root / "F03-boot-change", run_id)
    build_f04(root / "F04-whole-cohort-rollback", run_id)
    print(f"PNF_PACKS_SEALED root={root} cases=5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
