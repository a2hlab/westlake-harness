#!/usr/bin/env python3
"""Freeze/compare the exact five-stage canonical contract used by a run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List


CONTRACT_FILES = [
    "adapter/research/atoms/L03/A15/atom.yaml",
    "adapter/research/atoms/L03/A15/COMPARISON_DATA.md",
    "adapter/research/atoms/L03/A15/UNITY_INLINE_TLS_APERTURE_DESIGN.md",
    "adapter/research/atoms/L03/A15/UNITY_TLS_APERTURE_FIVE_STAGE_DESIGN.html",
    "adapter/research/atoms/L03/A15/UNITY_TLS_SELINUX_SPECIALIZATION_REQUIREMENTS_DESIGN.md",
    "adapter/research/atoms/L03/A15/UNITY_INLINE_ABI_FIVE_STAGE_IMPLEMENTATION_PLAN.md",
    "adapter/research/atoms/L03/A15/UNITY_INLINE_ABI_FIVE_STAGE_TEST_PLAN.md",
    "adapter/research/atoms/L03/A15/BIONIC_FIVE_STAGE_ACCEPTANCE_TESTS.md",
    "adapter/research/atoms/L03/A15/ATOM_TRACEABILITY.md",
    "adapter/research/atoms/L03/A15/ARCHITECTURE_REVIEW_CURRENT_20260712.md",
    "adapter/research/atoms/L03/A15/CLAUDE_HEADLESS_REVIEW_20260712.md",
    "adapter/research/atoms/L03/A15/evidence/reviews/BIONIC_FIVE_STAGE_HEADLESS_REVIEW_R1.md",
    "adapter/research/atoms/L03/A15/evidence/reviews/BIONIC_FIVE_STAGE_HEADLESS_REVIEW_R2.md",
    "adapter/research/atoms/L03/A15/evidence/reviews/BIONIC_FIVE_STAGE_HEADLESS_REVIEW_R3.md",
    "adapter/research/atoms/L03/A15/acceptance/registries/error_codes.tsv",
    "adapter/research/atoms/L03/A15/acceptance/registries/negative_cases.tsv",
    "adapter/research/atoms/L03/A15/acceptance/registries/zero_metrics.tsv",
    "adapter/research/atoms/L03/A15/acceptance/registries/state_equations.tsv",
    "adapter/research/atoms/L03/A15/acceptance/registries/reject_cases.tsv",
    "adapter/research/atoms/L03/A15/acceptance/tests/validate_registries.py",
    "adapter/research/atoms/L03/A15/evidence/imports/02c-verifier-20260712/MERGE_MANIFEST.json",
    "adapter/research/atoms/L03/A15/evidence/imports/02c-verifier-20260712/verify_import.py",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/MANIFEST.sha256",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/README.md",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/REPORT.md",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/build_target_in_container.sh",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/fixture/test_fixture_signing.c",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/fixture/test_fixture_signing.h",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/include/wlnc_aperture_fixture.h",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/run_all.sh",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/run_host_tests.sh",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/src/aperture_store_readback_aarch64.S",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/src/aperture_store_readback_host.c",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/src/aperture_writer.c",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/target/fixture_getrandom_aarch64.S",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/target/fixture_main.c",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/target/fixture_start_aarch64.S",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/target/reservation_owner_aarch64.S",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/tests/test_aperture_writer.c",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/verify_target_artifacts.py",
    "adapter/framework/native-compat/tests/aperture_writer_fixture/wlnc_aperture_fixture.map",
    "adapter/scripts/run_bionic_musl_regression.sh",
    "adapter/scripts/write_bionic_musl_regression_report.py",
    "adapter/scripts/freeze_bionic_musl_contract.py",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL five-stage contract snapshot: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_local(path: Path, project: Path) -> Path:
    resolved = path.resolve(strict=True)
    try:
        resolved.relative_to(project)
    except ValueError:
        fail(f"path escaped project: {path}")
    if path.is_symlink() or not path.is_file():
        fail(f"non-regular or symlinked contract input: {path}")
    return resolved


def snapshot(project: Path) -> Dict[str, object]:
    rows: List[Dict[str, object]] = []
    aggregate = hashlib.sha256()
    for relative in CONTRACT_FILES:
        path = require_local(project / relative, project)
        digest = sha256(path)
        size = path.stat().st_size
        row = {"path": relative, "sha256": digest, "size": size}
        rows.append(row)
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\n")
    return {
        "schema": "westlake-bionic-musl-contract-snapshot-v1",
        "file_count": len(rows),
        "aggregate_sha256": aggregate.hexdigest(),
        "files": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", type=Path)
    action.add_argument("--compare", type=Path)
    args = parser.parse_args()

    project = args.project_root.resolve(strict=True)
    current = snapshot(project)
    if args.write is not None:
        output = args.write
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            output.resolve().relative_to(project)
        except ValueError:
            fail(f"snapshot output escaped project: {output}")
        if output.is_symlink():
            fail(f"symlinked snapshot output: {output}")
        output.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"PASS contract_frozen files={current['file_count']} "
            f"aggregate={current['aggregate_sha256']}"
        )
        return 0

    expected_path = require_local(args.compare, project)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    if expected != current:
        expected_rows = {row["path"]: row for row in expected.get("files", [])}
        current_rows = {row["path"]: row for row in current["files"]}
        changed = sorted(
            path
            for path in set(expected_rows) | set(current_rows)
            if expected_rows.get(path) != current_rows.get(path)
        )
        fail(f"canonical contract drifted during regression: {changed}")
    print(
        f"PASS contract_stable files={current['file_count']} "
        f"aggregate={current['aggregate_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
