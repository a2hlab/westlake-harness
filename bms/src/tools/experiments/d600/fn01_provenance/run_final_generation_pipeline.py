#!/usr/bin/env python3
"""Run a fresh boot bake, resolve its receipt, and pack one Fn01 bundle.

This controller runs on the builder host after ``boot-work/incoming`` has been
prepared.  It does not deploy.  A template must contain exactly one producer
receipt ref whose path is ``@FRESH_BOOT_PRODUCER_RECEIPT@``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

try:
    from tools.experiments.d600.fn01_provenance.final_generation_controller import (
        ContractError,
        Controller,
        pack,
        sha256,
        write_json,
    )
except ModuleNotFoundError:  # direct script execution from its own directory
    from final_generation_controller import (  # type: ignore[no-redef]
        ContractError,
        Controller,
        pack,
        sha256,
        write_json,
    )


BOOT_RECEIPT_MARKER = "@FRESH_BOOT_PRODUCER_RECEIPT@"


def resolve_spec_template(
    template: dict[str, Any],
    producer_receipt_path: Path,
    frozen_build_id: str,
) -> dict[str, Any]:
    if template.get("frozen_build_id") != frozen_build_id:
        raise ContractError("spec template frozen_build_id mismatch")
    refs = template.get("producer_receipts")
    if not isinstance(refs, list):
        raise ContractError("spec template producer_receipts must be a list")
    matching = [ref for ref in refs if ref.get("path") == BOOT_RECEIPT_MARKER]
    if len(matching) != 1:
        raise ContractError("spec template needs exactly one fresh boot receipt marker")
    receipt = json.loads(producer_receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema_version") != "bridge.fn01.producer-receipt.v1":
        raise ContractError("fresh boot producer receipt schema mismatch")
    if receipt.get("producer_kind") != "boot":
        raise ContractError("fresh boot producer receipt kind mismatch")
    if receipt.get("frozen_build_id") != frozen_build_id:
        raise ContractError("fresh boot producer receipt frozen_build_id mismatch")
    matching[0].clear()
    matching[0].update(
        {
            "path": str(producer_receipt_path.resolve()),
            "sha256": sha256(producer_receipt_path),
        }
    )
    return template


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boot-worker", type=Path, required=True)
    parser.add_argument("--aosp-root", type=Path, required=True)
    parser.add_argument("--boot-work", type=Path, required=True)
    parser.add_argument("--frozen-build-id", required=True)
    parser.add_argument("--spec-template", type=Path, required=True)
    parser.add_argument("--resolved-spec", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--request-eligible", action="store_true")
    args = parser.parse_args(argv)

    failure_report = {
        "schema_version": "bridge.fn01.final-generation-pipeline.v1",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "frozen_build_id": args.frozen_build_id,
        "status": {
            "pipeline_pass": False,
            "eligible_for_deploy": False,
            "device_verified": False,
            "formal_verdict": "NOT_ISSUED",
        },
    }
    try:
        for path, label in (
            (args.resolved_spec, "resolved spec"),
            (args.report, "report"),
            (args.output_dir, "output directory"),
        ):
            if path.exists():
                raise ContractError(f"refuse existing {label}: {path}")
        command = [
            "python3",
            str(args.boot_worker.resolve()),
            "--aosp-root",
            str(args.aosp_root.resolve()),
            "--work",
            str(args.boot_work.resolve()),
            "--frozen-build-id",
            args.frozen_build_id,
        ]
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        failure_report["boot_builder"] = {
            "argv": command,
            "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
            "stdout": result.stdout,
        }
        if result.returncode != 0:
            raise ContractError(f"fresh boot builder failed rc={result.returncode}")
        producer_receipt = args.boot_work.resolve() / "producer-receipt.json"
        if not producer_receipt.is_file():
            raise ContractError("fresh boot builder did not write producer-receipt.json")
        template = json.loads(args.spec_template.read_text(encoding="utf-8"))
        resolved = resolve_spec_template(
            template, producer_receipt, args.frozen_build_id
        )
        write_json(args.resolved_spec, resolved)
        validation = Controller(args.resolved_spec, args.request_eligible).validate()
        identity = pack(validation, args.output_dir)
        report = validation.report
        report["pipeline"] = failure_report["boot_builder"]
        report["packed_generation"] = identity
        report["status"]["pipeline_pass"] = True
        write_json(args.report, report)
    except Exception as error:
        failure_report["failure"] = f"{type(error).__name__}: {error}"
        write_json(args.report, failure_report)
        print(f"REPORT={args.report.resolve()}")
        print("PIPELINE_PASS=false")
        print("ELIGIBLE_FOR_DEPLOY=false")
        print("DEVICE_VERIFIED=false")
        print("FORMAL_VERDICT=NOT_ISSUED")
        print(f"FAILURE={failure_report['failure']}")
        return 1
    print(f"REPORT={args.report.resolve()}")
    print("PIPELINE_PASS=true")
    print(f"ELIGIBLE_FOR_DEPLOY={str(validation.eligible).lower()}")
    print("DEVICE_VERIFIED=false")
    print("FORMAL_VERDICT=NOT_ISSUED")
    print(f"GENERATION_ID={identity['generation_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
