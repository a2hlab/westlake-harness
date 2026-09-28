#!/usr/bin/env python3
"""Independently re-read an APK-only CardWords extraction receipt."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import stat
import subprocess
import zipfile
from pathlib import Path


CONTRACT = "westlake.unity_apk_binary_only.v1"
SCHEMA = "westlake.cardwords.native_bundle.v1"
GEN_SCHEMA = "westlake.l03_a12.provider_closure.v3"
PAIR_SCHEMA = "westlake.unity_apk_source_pair.v1"
APK_RELATIVE = Path("frozen/product_inputs/cardwords-current/canonical/selfcontained_cardwords.apk")
EXPECTED_APK_SIZE = 66377217
EXPECTED_APK_SHA256 = "435f0ebbf99b5f5ae76aecb411da7684052a92ef0b6aee18d50afa6a98210626"
EXPECTED = {
    "libmain": "lib/arm64-v8a/libmain.so",
    "libunity": "lib/arm64-v8a/libunity.so",
    "libil2cpp": "lib/arm64-v8a/libil2cpp.so",
    "lib_burst_generated": "lib/arm64-v8a/lib_burst_generated.so",
}
BUILD_ID_RE = re.compile(r"[0-9a-f]{16,128}")


class Reject(RuntimeError):
    pass


def regular(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"{label} missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise Reject(f"{label} must be a regular non-symlink file: {path}")


def directory(path: Path, label: str) -> None:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"{label} missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
        raise Reject(f"{label} must be a real non-symlink directory: {path}")


def executable_tool(path: Path) -> tuple[Path, str]:
    try:
        mode = path.lstat().st_mode
    except OSError as exc:
        raise Reject(f"readelf missing: {path}: {exc}") from exc
    if stat.S_ISLNK(mode):
        resolved = path.resolve(strict=True)
        regular(resolved, "resolved readelf")
        if resolved.parent != path.parent.resolve():
            raise Reject("readelf symlink escapes its official bin directory")
    elif stat.S_ISREG(mode):
        resolved = path
    else:
        raise Reject("readelf must be a regular file or in-bin multicall symlink")
    if not os.access(path, os.X_OK):
        raise Reject("readelf is not executable")
    return resolved, sha256(resolved)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path, label: str) -> dict:
    regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Reject(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise Reject(f"{label} root must be an object")
    return value


def run(readelf: Path, path: Path, *args: str) -> str:
    result = subprocess.run(
        [str(readelf), *args, str(path)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        raise Reject(f"readelf failed for {path}: rc={result.returncode}")
    return result.stdout


def inspect(readelf: Path, path: Path) -> dict:
    header = run(readelf, path, "--file-header", "--wide")
    dynamic = run(readelf, path, "--dynamic", "--wide")
    notes = run(readelf, path, "--notes", "--wide")
    if not ("ELF64" in header or "Class: 64-bit" in header):
        raise Reject(f"not ELF64: {path}")
    if not any(token in header for token in ("AArch64", "AARCH64", "aarch64")):
        raise Reject(f"not AArch64: {path}")
    ids = [x.lower() for x in re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)]
    if len(ids) != 1 or BUILD_ID_RE.fullmatch(ids[0]) is None:
        raise Reject(f"invalid BuildID: {path}")
    sonames = re.findall(r"(?:\(SONAME\)|\bSONAME\b).*?\[([^]]+)\]", dynamic)
    needed = re.findall(r"(?:\(NEEDED\)|\bNEEDED\b).*?\[([^]]+)\]", dynamic)
    if len(sonames) > 1:
        raise Reject(f"ambiguous SONAME: {path}")
    return {
        "elf_machine": "AArch64",
        "build_id": ids[0],
        "soname": sonames[0] if sonames else None,
        "dt_needed": needed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-root", required=True, type=Path)
    parser.add_argument("--extraction-root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    args = parser.parse_args()

    adapter_root = Path(__file__).resolve().parent.parent
    generation_root = args.generation_root.absolute()
    extraction_root = args.extraction_root.absolute()
    receipt_path = args.receipt.absolute()
    readelf = args.readelf.absolute()
    directory(generation_root, "generation root")
    directory(extraction_root, "extraction root")
    resolved_readelf, readelf_sha = executable_tool(readelf)
    if receipt_path != extraction_root / "native-bundle.json":
        raise Reject("receipt must be EXTRACTION_ROOT/native-bundle.json")
    receipt = load_json(receipt_path, "extraction receipt")
    generation_manifest = generation_root / "meta/generation.json"
    generation = load_json(generation_manifest, "generation manifest")
    if (generation_root / "meta/INCOMPLETE").exists():
        raise Reject("generation is INCOMPLETE")
    generation_id = generation.get("generation_id")
    if generation.get("schema") != GEN_SCHEMA or generation_root.name != generation_id:
        raise Reject("generation schema/identity mismatch")
    if generation_root.parent.resolve() != (adapter_root / "generations").resolve():
        raise Reject("generation root is outside GroundTruth build generations")
    expected_extraction = adapter_root / "build/generation-private-cardwords" / generation_id
    if extraction_root.resolve() != expected_extraction.resolve():
        raise Reject("old, reused, or foreign generation extraction path")
    if receipt.get("schema") != SCHEMA or receipt.get("contract_id") != CONTRACT:
        raise Reject("receipt schema/contract mismatch")
    if receipt.get("status") != "apk_binary_only_pass":
        raise Reject("receipt is not an APK-only pass")
    if receipt.get("product_class") != "unity_apk_binary_only":
        raise Reject("fixture or non-product receipt masquerading as Unity product")
    manifest_sha = sha256(generation_manifest)
    expected_token = f"wlgen-{generation_id}-{manifest_sha}"
    if receipt.get("generation_id") != generation_id:
        raise Reject("mixed generation ID")
    if receipt.get("generation_manifest_sha256") != manifest_sha:
        raise Reject("mixed generation manifest SHA256")
    if receipt.get("generation_token") != expected_token:
        raise Reject("mixed generation token")
    if receipt.get("generation_root") != str(generation_root):
        raise Reject("generation path mismatch")

    apk = adapter_root / APK_RELATIVE
    regular(apk, "GroundTruth packaged APK")
    apk_item = receipt.get("apk")
    if not isinstance(apk_item, dict) or apk_item.get("source_kind") != "packaged_apk":
        raise Reject("loose DSO or non-APK source is forbidden")
    expected_apk_item = {
        "path": str(apk.absolute()),
        "groundtruth_relative_path": str(APK_RELATIVE),
        "size": EXPECTED_APK_SIZE,
        "sha256": EXPECTED_APK_SHA256,
    }
    for key, value in expected_apk_item.items():
        if apk_item.get(key) != value:
            raise Reject(f"APK {key} mismatch")
    if apk.stat().st_size != EXPECTED_APK_SIZE or sha256(apk) != EXPECTED_APK_SHA256:
        raise Reject("current GroundTruth APK identity mismatch")
    pair = receipt.get("source_pair_receipt")
    if not isinstance(pair, dict):
        raise Reject("source-pair receipt binding missing")
    pair_path = Path(pair.get("path", "")).absolute()
    pair_value = load_json(pair_path, "source-pair receipt")
    if pair.get("sha256") != sha256(pair_path):
        raise Reject("source-pair receipt SHA256 mismatch")
    if pair_value.get("schema") != PAIR_SCHEMA or pair_value.get("contract_id") != CONTRACT:
        raise Reject("source-pair receipt schema mismatch")
    if pair_value.get("cmp_equal") is not True:
        raise Reject("origin/project APK equality not proven")

    extraction = receipt.get("extraction")
    if not isinstance(extraction, dict):
        raise Reject("extraction block missing")
    if extraction.get("method") != "python_zipfile_direct_no_loose_fallback":
        raise Reject("loose DSO fallback or unknown extraction method")
    if extraction.get("output_root") != str(extraction_root) or extraction.get("exit_code") != 0:
        raise Reject("extraction path/exit mismatch")
    if extraction.get("inspection_tool") != {
        "logical_path": str(readelf),
        "resolved_path": str(resolved_readelf),
        "resolved_sha256": readelf_sha,
    }:
        raise Reject("inspection tool identity mismatch")
    records = receipt.get("artifacts")
    if not isinstance(records, list) or len(records) != len(EXPECTED):
        raise Reject("required APK entry set incomplete")
    by_role = {}
    for item in records:
        if not isinstance(item, dict) or item.get("role") in by_role:
            raise Reject("malformed or duplicate artifact role")
        by_role[item.get("role")] = item
    if set(by_role) != set(EXPECTED):
        raise Reject("missing or unsupported APK artifact role")

    allowed_files = {receipt_path.resolve()}
    with zipfile.ZipFile(apk, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise Reject("APK contains duplicate ZIP entry names")
        for role, entry in EXPECTED.items():
            item = by_role[role]
            if item.get("source_kind") != "apk_zip_entry":
                raise Reject(f"loose DSO forbidden for role={role}")
            if item.get("zip_entry") != entry or item.get("path") != entry:
                raise Reject(f"ZIP entry/path mismatch for role={role}")
            try:
                info = archive.getinfo(entry)
            except KeyError as exc:
                raise Reject(f"required APK entry missing: {entry}") from exc
            target = extraction_root / entry
            regular(target, f"extracted {role}")
            try:
                target.resolve().relative_to(extraction_root.resolve())
            except ValueError as exc:
                raise Reject(f"extracted path escapes root: {role}") from exc
            allowed_files.add(target.resolve())
            crc = 0
            with target.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    crc = binascii.crc32(block, crc)
            expected_zip = {
                "zip_crc32": f"{info.CRC:08x}",
                "compression_method": info.compress_type,
                "compressed_size": info.compress_size,
                "uncompressed_size": info.file_size,
            }
            for key, value in expected_zip.items():
                if item.get(key) != value:
                    raise Reject(f"ZIP {key} mismatch for role={role}")
            if target.stat().st_size != info.file_size or (crc & 0xFFFFFFFF) != info.CRC:
                raise Reject(f"extracted size/CRC mismatch for role={role}")
            if item.get("sha256") != sha256(target):
                raise Reject(f"extracted SHA256 mismatch for role={role}")
            identity = inspect(readelf, target)
            for key, value in identity.items():
                if item.get(key) != value:
                    raise Reject(f"ELF {key} mismatch for role={role}")
    actual_files = {p.resolve() for p in extraction_root.rglob("*") if p.is_file()}
    if actual_files != allowed_files:
        raise Reject("unexpected loose or unreceipted file in extraction root")
    if receipt.get("device_verified") is not False or receipt.get("engine_started") is not False:
        raise Reject("host receipt contains promoted runtime state")
    print(
        f"UNITY_APK_BINARY_ONLY_RECEIPT_PASS generation={generation_id} "
        f"apk_sha256={EXPECTED_APK_SHA256} artifacts={len(EXPECTED)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Reject, OSError, zipfile.BadZipFile) as exc:
        print(f"UNITY_APK_BINARY_ONLY_RECEIPT_REJECT {exc}", file=os.sys.stderr)
        raise SystemExit(1)
