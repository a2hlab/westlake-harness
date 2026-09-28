#!/usr/bin/env python3
"""Read every planned canonical adapter byte back from the ext4 system image."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


PLAN_SCHEMA = "westlake.wukong100.adapter_image_plan.v1"
BUILD_ID_RE = re.compile(r"Build ID:\s*([0-9a-fA-F]+)")
MODE_RE = re.compile(r"Mode:\s*0*([0-7]{3,4})")
USER_GROUP_RE = re.compile(r"User:\s*(\d+)\s+Group:\s*(\d+)")
SELINUX_RE = re.compile(r"u:object_r:[a-zA-Z0-9_]+:s0")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def debugfs(debugfs: Path, image: Path, command: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [str(debugfs), "-R", command, str(image)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_image_file(debugfs_path: Path, image: Path, destination: str) -> bytes:
    result = debugfs(debugfs_path, image, f"cat {destination}")
    stderr = result.stderr.decode("utf-8", "replace")
    if (
        result.returncode != 0
        or "File not found" in stderr
        or "not found" in stderr.lower()
        or not result.stdout
    ):
        raise ValueError(
            f"image entry missing: {destination} rc={result.returncode} stderr={stderr.strip()}"
        )
    return result.stdout


def build_id_bytes(value: bytes, readelf: Path) -> str | None:
    if value[:4] != b"\x7fELF":
        return None
    with tempfile.NamedTemporaryFile(prefix="westlake-image-elf-", delete=True) as stream:
        stream.write(value)
        stream.flush()
        result = subprocess.run(
            [str(readelf), "--notes", "--wide", stream.name],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        raise ValueError(f"readelf failed on image bytes: {result.stderr.strip()}")
    match = BUILD_ID_RE.search(result.stdout)
    if not match:
        raise ValueError("ELF image bytes lack Build-ID")
    return match.group(1).lower()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--debugfs", type=Path, required=True)
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"unsupported image plan schema: {plan.get('schema')}")
    if args.output.exists() or args.output.is_symlink():
        raise ValueError(f"refusing to replace audit: {args.output}")

    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for entry in plan["entries"]:
        destination = entry["destination"]
        try:
            value = read_image_file(args.debugfs, args.image, destination)
            actual_sha = sha256_bytes(value)
            actual_build_id = build_id_bytes(value, args.readelf)
            stat_result = debugfs(args.debugfs, args.image, f"stat {destination}")
            stat_text = stat_result.stdout.decode("utf-8", "replace")
            mode_match = MODE_RE.search(stat_text)
            owner_match = USER_GROUP_RE.search(stat_text)
            mode = mode_match.group(1).zfill(4) if mode_match else None
            uid = int(owner_match.group(1)) if owner_match else None
            gid = int(owner_match.group(2)) if owner_match else None
            ea_result = debugfs(args.debugfs, args.image, f"ea_list {destination}")
            ea_text = (
                ea_result.stdout.decode("utf-8", "replace")
                + ea_result.stderr.decode("utf-8", "replace")
            )
            label_match = SELINUX_RE.search(ea_text)
            label = label_match.group(0) if label_match else None
            checks = {
                "sha_match": actual_sha == entry["sha256"],
                "size_match": len(value) == entry["size"],
                "build_id_match": actual_build_id == entry["build_id"],
                "mode_match": mode == entry["mode"],
                "uid_match": uid == entry["uid"],
                "gid_match": gid == entry["gid"],
                "selinux_match": label == entry["selinux_label"],
            }
            if entry["build_id"] is None:
                checks["build_id_match"] = actual_build_id is None
            if not all(checks.values()):
                failures.append(
                    f"{destination}: "
                    + ",".join(key for key, passed in checks.items() if not passed)
                )
            rows.append(
                {
                    "destination": destination,
                    "expected_sha256": entry["sha256"],
                    "actual_sha256": actual_sha,
                    "expected_build_id": entry["build_id"],
                    "actual_build_id": actual_build_id,
                    "expected_mode": entry["mode"],
                    "actual_mode": mode,
                    "expected_uid": entry["uid"],
                    "actual_uid": uid,
                    "expected_gid": entry["gid"],
                    "actual_gid": gid,
                    "expected_selinux_label": entry["selinux_label"],
                    "actual_selinux_label": label,
                    **checks,
                }
            )
        except ValueError as exc:
            failures.append(str(exc))
            rows.append({"destination": destination, "error": str(exc)})

    forbidden = "/system/android/lib64/libart_runtime_stubs.so"
    if forbidden not in {entry["destination"] for entry in plan["entries"]}:
        probe = debugfs(args.debugfs, args.image, f"stat {forbidden}")
        probe_text = (
            probe.stdout.decode("utf-8", "replace")
            + probe.stderr.decode("utf-8", "replace")
        )
        forbidden_absent = "not found" in probe_text.lower()
        if not forbidden_absent:
            failures.append(f"forbidden stale broad stub present: {forbidden}")
    else:
        forbidden_absent = False
        failures.append(f"image plan itself contains forbidden broad stub: {forbidden}")

    document = {
        "schema": "westlake.wukong100.adapter_system_image_audit.v1",
        "scope": "HOST_ARTIFACT_VERIFIED / NOT_DEVICE_VERIFIED",
        "generation_id": plan["generation_id"],
        "image_path": str(args.image.absolute()),
        "image_sha256": sha256_file(args.image),
        "image_size": args.image.stat().st_size,
        "image_plan_path": str(args.plan.absolute()),
        "image_plan_sha256": sha256_file(args.plan),
        "entry_count": len(rows),
        "exact_entry_count": sum(
            1
            for row in rows
            if "error" not in row
            and all(
                row[key]
                for key in (
                    "sha_match",
                    "size_match",
                    "build_id_match",
                    "mode_match",
                    "uid_match",
                    "gid_match",
                    "selinux_match",
                )
            )
        ),
        "forbidden_broad_stub_absent": forbidden_absent,
        "all_exact": not failures,
        "failures": failures,
        "entries": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if failures:
        print(
            f"IMAGE_AUDIT_FAIL generation={plan['generation_id']} failures={len(failures)} "
            f"output={args.output}"
        )
        return 1
    print(
        f"IMAGE_AUDIT_PASS generation={plan['generation_id']} entries={len(rows)} "
        f"image_sha256={document['image_sha256']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
