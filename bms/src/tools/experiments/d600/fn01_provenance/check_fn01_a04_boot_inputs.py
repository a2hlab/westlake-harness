#!/usr/bin/env python3
"""Read-only checker for the Fn01.A04 current-generation boot input plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence


SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remote(host: str, command: str) -> str:
    result = subprocess.run(
        ["ssh", host, command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"remote probe failed rc={result.returncode}: {result.stdout}")
    return result.stdout.strip()


def remote_sha(host: str, path: str) -> str:
    output = remote(host, f"sha256sum {path}")
    value = output.split()[0] if output.split() else ""
    if not SHA_RE.fullmatch(value):
        raise RuntimeError(f"invalid sha256sum output for {path}: {output!r}")
    return value


def remote_dex_entries(host: str, path: str) -> int:
    output = remote(
        host,
        f"unzip -Z1 {path} | grep -E -c '^classes([0-9]+)?[.]dex$' || true",
    )
    if not output.isdigit():
        raise RuntimeError(f"invalid dex-entry count for {path}: {output!r}")
    return int(output)


def remote_bytes(host: str, path: str) -> int:
    output = remote(host, f"stat -c %s {path}")
    if not output.isdigit():
        raise RuntimeError(f"invalid byte count for {path}: {output!r}")
    return int(output)


def canonical_java_manifest_sha256(root: Path) -> tuple[int, str]:
    lines = []
    files = sorted(path for path in root.rglob("*.java") if path.is_file())
    for path in files:
        lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}\n")
    return len(files), hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("/opt/Bridge"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    plan_path = args.plan.resolve()
    plan: dict[str, Any] = json.loads(plan_path.read_text(encoding="utf-8"))
    host = plan["builder_host"]
    parent = plan["parent_generation"]
    identity_path = root / parent["identity_path"]
    if sha256(identity_path) != parent["identity_sha256"]:
        raise SystemExit("parent generation identity hash mismatch")

    runtime_roles = plan["runtime_bootclasspath_order"]
    dex2oat_roles = plan["dex2oat_bootclasspath_order"]
    by_role = {item["role"]: item for item in plan["inputs"]}
    if len(by_role) != len(plan["inputs"]):
        raise SystemExit("duplicate boot input role")
    if not set(runtime_roles).issubset(by_role):
        raise SystemExit("runtime bootclasspath references unknown roles")
    if not set(dex2oat_roles).issubset(by_role):
        raise SystemExit("dex2oat bootclasspath references unknown roles")

    observations: list[dict[str, Any]] = []
    missing: list[str] = []
    unadmitted: list[str] = []
    mismatches: list[str] = []
    for item in plan["inputs"]:
        role = item["role"]
        path = item.get("path")
        expected = item.get("sha256")
        observation: dict[str, Any] = {
            "role": role,
            "state": item["state"],
            "admitted_to_parent_generation": item["admitted_to_parent_generation"],
        }
        if path is None:
            missing.append(role)
            observation["observed"] = "MISSING_BY_PLAN"
            observations.append(observation)
            continue
        if Path(path).is_absolute():
            actual = remote_sha(host, path)
            actual_bytes = remote_bytes(host, path)
            if item["kind"] == "dex-jar":
                dex_entries = remote_dex_entries(host, path)
                observation["dex_entries"] = dex_entries
                if dex_entries != item["dex_entries"]:
                    mismatches.append(f"{role}:dex_entries")
        else:
            local = (root / path).resolve()
            if root not in local.parents:
                raise SystemExit(f"local plan path escapes root: {path}")
            actual = sha256(local)
            actual_bytes = local.stat().st_size
            if item["kind"] == "dex-jar":
                listing = subprocess.run(
                    ["unzip", "-Z1", str(local)],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                dex_entries = sum(
                    1
                    for line in listing.stdout.splitlines()
                    if re.fullmatch(r"classes([0-9]+)?[.]dex", line)
                )
                observation["dex_entries"] = dex_entries
                if dex_entries != item["dex_entries"]:
                    mismatches.append(f"{role}:dex_entries")
        observation["observed_sha256"] = actual
        observation["expected_sha256"] = expected
        observation["hash_match"] = actual == expected
        observation["observed_bytes"] = actual_bytes
        if actual != expected:
            mismatches.append(f"{role}:sha256")
        expected_bytes = item.get("bytes")
        if expected_bytes is not None:
            observation["expected_bytes"] = expected_bytes
            observation["bytes_match"] = actual_bytes == expected_bytes
            if actual_bytes != expected_bytes:
                mismatches.append(f"{role}:bytes")
        producer = item.get("producer")
        if producer:
            producer_observation: dict[str, Any] = {}
            for producer_role, path_key, hash_key in (
                ("source_jar", "source_jar", "source_jar_sha256"),
                ("tool", "tool", "tool_sha256"),
            ):
                if path_key not in producer or hash_key not in producer:
                    continue
                producer_path = producer[path_key]
                producer_actual = remote_sha(host, producer_path)
                producer_expected = producer[hash_key]
                producer_observation[producer_role] = {
                    "path": producer_path,
                    "observed_sha256": producer_actual,
                    "expected_sha256": producer_expected,
                    "hash_match": producer_actual == producer_expected,
                }
                if producer_actual != producer_expected:
                    mismatches.append(f"{role}:producer:{producer_role}:sha256")
            active_source = item.get("active_source")
            active_manifest = item.get("active_source_manifest_sha256")
            if active_source and active_manifest:
                source_root = (root / active_source).resolve()
                if root not in source_root.parents:
                    raise SystemExit(f"active source escapes root: {active_source}")
                source_count, source_sha = canonical_java_manifest_sha256(source_root)
                source_expected_count = item["active_source_file_count"]
                producer_observation["active_source_manifest"] = {
                    "schema": item["active_source_manifest_schema"],
                    "observed_file_count": source_count,
                    "expected_file_count": source_expected_count,
                    "observed_sha256": source_sha,
                    "expected_sha256": active_manifest,
                    "match": (
                        source_count == source_expected_count
                        and source_sha == active_manifest
                    ),
                }
                if source_count != source_expected_count:
                    mismatches.append(f"{role}:producer:source_file_count")
                if source_sha != active_manifest:
                    mismatches.append(f"{role}:producer:source_manifest_sha256")
            observation["producer_observation"] = producer_observation
        if not item["admitted_to_parent_generation"]:
            unadmitted.append(role)
        observations.append(observation)

    report = {
        "schema_version": "bridge.fn01.a04-boot-input-check.v1",
        "plan": {
            "path": str(plan_path),
            "sha256": sha256(plan_path),
        },
        "parent_generation_identity": {
            "path": str(identity_path),
            "sha256": sha256(identity_path),
        },
        "observations": observations,
        "missing_roles": missing,
        "candidate_roles_not_yet_admitted": unadmitted,
        "mismatches": mismatches,
        "status": {
            "candidate_byte_probe_pass": not mismatches,
            "boot_builder_ready": not missing and not unadmitted and not mismatches,
            "build_pass": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
        "next_action": (
            "core-icu4j 与 adapter-mainline-stubs 当前源码 producer 均已证实；"
            "由通用 builder 从 frozen staging 重放，再把全部 host tools、9 个 BCP jar "
            "和 27 个 boot 输出封入新的 generation closure。"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"REPORT={args.output.resolve()}")
    print(f"CANDIDATE_BYTE_PROBE_PASS={str(not mismatches).lower()}")
    print(f"BOOT_BUILDER_READY={str(report['status']['boot_builder_ready']).lower()}")
    print(f"MISSING_ROLES={','.join(missing)}")
    print(f"UNADMITTED_ROLES={','.join(unadmitted)}")
    print("BUILD_PASS=false")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    return 0 if not mismatches else 2


if __name__ == "__main__":
    raise SystemExit(main())
