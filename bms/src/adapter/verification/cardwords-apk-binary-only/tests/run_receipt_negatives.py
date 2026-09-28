#!/usr/bin/env python3
"""Run fail-closed controls against a temporary APK-only extraction."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter-root", required=True, type=Path)
    parser.add_argument("--source-pair-receipt", required=True, type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.adapter_root.absolute()
    gid = f"apk-binary-only-negative-{os.getpid()}"
    gen = root / "generations" / gid
    extract = root / "build/generation-private-cardwords" / gid
    backup = root / "build/cardwords-apk-binary-only-test-backup" / gid
    receipt = extract / "native-bundle.json"
    extractor = root / "scripts/extract_cardwords_apk_binary_only.py"
    verifier = root / "scripts/verify_cardwords_apk_binary_only_receipt.py"
    apk = root / "frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk"
    if gen.exists() or extract.exists() or backup.exists():
        raise RuntimeError("test path unexpectedly exists")
    results: list[dict] = []
    try:
        (gen / "meta").mkdir(parents=True)
        (gen / "meta/generation.json").write_text(json.dumps({
            "schema": "westlake.l03_a12.provider_closure.v3",
            "generation_id": gid,
            "artifacts": [{"role": "test-only-not-product", "path": "unused", "sha256": "0" * 64}],
        }, sort_keys=True) + "\n")
        extract_cmd = [sys.executable, str(extractor), "--generation-root", str(gen),
                       "--apk", str(apk), "--source-pair-receipt", str(args.source_pair_receipt),
                       "--readelf", str(args.readelf), "--output-root", str(extract)]
        verify_cmd = [sys.executable, str(verifier), "--generation-root", str(gen),
                      "--extraction-root", str(extract), "--receipt", str(receipt),
                      "--readelf", str(args.readelf)]
        positive = run(extract_cmd)
        results.append({"name": "positive_extract", "rc": positive.returncode, "output": positive.stdout.strip()})
        if positive.returncode:
            raise RuntimeError(f"positive extraction failed: {positive.stdout.strip()}")
        verified = run(verify_cmd)
        results.append({"name": "positive_validate", "rc": verified.returncode, "output": verified.stdout.strip()})
        if verified.returncode:
            raise RuntimeError(f"positive validation failed: {verified.stdout.strip()}")
        reuse = run(extract_cmd)
        results.append({"name": "reuse_old_generation_path", "rc": reuse.returncode, "output": reuse.stdout.strip()})
        if reuse.returncode == 0:
            raise RuntimeError("reused generation path was accepted")
        shutil.copytree(extract, backup)

        mutations = {
            "wrong_apk_sha": lambda d: d["apk"].__setitem__("sha256", "0" * 64),
            "missing_entry": lambda d: d["artifacts"].pop(),
            "loose_dso": lambda d: d["artifacts"][0].__setitem__("source_kind", "loose_dso"),
            "old_generation": lambda d: d.__setitem__("generation_id", "r44-old-generation"),
            "fixture_masquerade": lambda d: d.__setitem__("product_class", "fixture"),
        }
        for name, mutate in mutations.items():
            shutil.rmtree(extract)
            shutil.copytree(backup, extract)
            data = json.loads(receipt.read_text())
            mutate(data)
            receipt.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
            result = run(verify_cmd)
            results.append({"name": name, "rc": result.returncode, "output": result.stdout.strip()})
            if result.returncode == 0:
                raise RuntimeError(f"negative accepted: {name}")

        shutil.rmtree(extract)
        shutil.copytree(backup, extract)
        target = extract / "lib/arm64-v8a/libmain.so"
        with target.open("r+b") as stream:
            first = stream.read(1)
            stream.seek(0)
            stream.write(bytes([first[0] ^ 1]))
        result = run(verify_cmd)
        results.append({"name": "tampered_extracted_sha", "rc": result.returncode, "output": result.stdout.strip()})
        if result.returncode == 0:
            raise RuntimeError("tampered extracted DSO accepted")

        output = {
            "schema": "westlake.unity_apk_binary_only.negatives.v1",
            "status": "pass",
            "product_claim": False,
            "device_verified": False,
            "checks": results,
            "extractor_sha256": sha256(extractor),
            "validator_sha256": sha256(verifier),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
        print(f"UNITY_APK_BINARY_ONLY_NEGATIVES_PASS checks={len(results)} receipt={args.output}")
        return 0
    finally:
        shutil.rmtree(gen, ignore_errors=True)
        shutil.rmtree(extract, ignore_errors=True)
        shutil.rmtree(backup, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
