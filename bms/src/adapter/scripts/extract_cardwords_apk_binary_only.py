#!/usr/bin/env python3
"""Extract the exact CardWords ARM64 bundle from the packaged APK only."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath


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
GEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
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
    """Admit an official multicall tool symlink only within its own bin dir."""
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


def run_readelf(readelf: Path, path: Path, *args: str) -> str:
    result = subprocess.run(
        [str(readelf), *args, str(path)], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if result.returncode:
        raise Reject(f"readelf failed for {path}: rc={result.returncode}")
    return result.stdout


def inspect_elf(readelf: Path, path: Path) -> dict:
    header = run_readelf(readelf, path, "--file-header", "--wide")
    dynamic = run_readelf(readelf, path, "--dynamic", "--wide")
    notes = run_readelf(readelf, path, "--notes", "--wide")
    if not ("ELF64" in header or "Class: 64-bit" in header):
        raise Reject(f"not ELF64: {path}")
    if not any(token in header for token in ("AArch64", "AARCH64", "aarch64")):
        raise Reject(f"not AArch64: {path}")
    build_ids = [x.lower() for x in re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)]
    if len(build_ids) != 1 or BUILD_ID_RE.fullmatch(build_ids[0]) is None:
        raise Reject(f"requires one even 8-64-byte BuildID: {path}")
    sonames = re.findall(r"(?:\(SONAME\)|\bSONAME\b).*?\[([^]]+)\]", dynamic)
    needed = re.findall(r"(?:\(NEEDED\)|\bNEEDED\b).*?\[([^]]+)\]", dynamic)
    if len(sonames) > 1:
        raise Reject(f"ambiguous SONAME: {path}")
    return {
        "elf_machine": "AArch64",
        "build_id": build_ids[0],
        "soname": sonames[0] if sonames else None,
        "dt_needed": needed,
    }


def validate_source_pair(path: Path) -> str:
    value = load_json(path, "source-pair receipt")
    if value.get("schema") != PAIR_SCHEMA or value.get("contract_id") != CONTRACT:
        raise Reject("source-pair receipt schema/contract mismatch")
    if value.get("status") != "source_pair_pass" or value.get("cmp_equal") is not True:
        raise Reject("source-pair receipt is not a pass")
    for key in ("origin", "project"):
        item = value.get(key)
        if not isinstance(item, dict):
            raise Reject(f"source-pair {key} missing")
        if item.get("size") != EXPECTED_APK_SIZE or item.get("sha256") != EXPECTED_APK_SHA256:
            raise Reject(f"source-pair {key} identity mismatch")
    return sha256(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-root", required=True, type=Path)
    parser.add_argument("--apk", required=True, type=Path)
    parser.add_argument("--source-pair-receipt", required=True, type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()

    adapter_root = Path(__file__).resolve().parent.parent
    generation_root = args.generation_root.absolute()
    output_root = args.output_root.absolute()
    apk = args.apk.absolute()
    readelf = args.readelf.absolute()
    directory(adapter_root, "GroundTruth adapter root")
    directory(generation_root, "generation root")
    resolved_readelf, readelf_sha = executable_tool(readelf)
    generation_manifest = generation_root / "meta/generation.json"
    if (generation_root / "meta/INCOMPLETE").exists():
        raise Reject("generation is INCOMPLETE")
    generation = load_json(generation_manifest, "generation manifest")
    generation_id = generation.get("generation_id")
    if generation.get("schema") != GEN_SCHEMA:
        raise Reject("generation manifest schema mismatch")
    if not isinstance(generation_id, str) or GEN_RE.fullmatch(generation_id) is None:
        raise Reject("invalid generation ID")
    if generation_root.name != generation_id:
        raise Reject("mixed generation root/manifest")
    expected_gen_parent = adapter_root / "generations"
    if generation_root.parent.resolve() != expected_gen_parent.resolve():
        raise Reject("generation root is outside GroundTruth build generations")
    expected_apk = adapter_root / APK_RELATIVE
    if apk.resolve() != expected_apk.resolve():
        raise Reject("APK is not the exact GroundTruth packaged APK path")
    regular(apk, "GroundTruth packaged APK")
    if apk.stat().st_size != EXPECTED_APK_SIZE or sha256(apk) != EXPECTED_APK_SHA256:
        raise Reject("GroundTruth packaged APK size/SHA256 mismatch")
    pair_sha = validate_source_pair(args.source_pair_receipt.absolute())
    expected_output = adapter_root / "build/generation-private-cardwords" / generation_id
    if output_root.parent.resolve() / output_root.name != expected_output.parent.resolve() / expected_output.name:
        raise Reject("output root is not the new generation-private CardWords path")
    if output_root.exists() or output_root.is_symlink():
        raise Reject(f"refusing generation path reuse: {output_root}")

    manifest_sha = sha256(generation_manifest)
    token = f"wlgen-{generation_id}-{manifest_sha}"
    created = False
    try:
        output_root.mkdir(parents=True, exist_ok=False)
        created = True
        artifacts = []
        with zipfile.ZipFile(apk, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise Reject("APK contains duplicate ZIP entry names")
            for role, entry in EXPECTED.items():
                try:
                    info = archive.getinfo(entry)
                except KeyError as exc:
                    raise Reject(f"required APK entry missing: {entry}") from exc
                pure = PurePosixPath(entry)
                if pure.is_absolute() or ".." in pure.parts or info.is_dir():
                    raise Reject(f"unsafe APK entry: {entry}")
                target = output_root / entry
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as src, target.open("xb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                if target.stat().st_size != info.file_size:
                    raise Reject(f"extracted size mismatch: {entry}")
                crc = 0
                with target.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        crc = binascii.crc32(block, crc)
                if (crc & 0xFFFFFFFF) != info.CRC:
                    raise Reject(f"extracted CRC mismatch: {entry}")
                identity = inspect_elf(readelf, target)
                expected_soname = f"{role}.so"
                if identity["soname"] is not None and identity["soname"] != expected_soname:
                    raise Reject(f"SONAME mismatch: {entry}")
                artifacts.append({
                    "role": role,
                    "source_kind": "apk_zip_entry",
                    "zip_entry": entry,
                    "zip_crc32": f"{info.CRC:08x}",
                    "compression_method": info.compress_type,
                    "compressed_size": info.compress_size,
                    "uncompressed_size": info.file_size,
                    "path": entry,
                    "sha256": sha256(target),
                    **identity,
                })
        receipt = {
            "schema": SCHEMA,
            "contract_id": CONTRACT,
            "status": "apk_binary_only_pass",
            "product_class": "unity_apk_binary_only",
            "generation_id": generation_id,
            "generation_manifest_sha256": manifest_sha,
            "generation_token": token,
            "generation_root": str(generation_root),
            "apk": {
                "source_kind": "packaged_apk",
                "path": str(apk),
                "groundtruth_relative_path": str(APK_RELATIVE),
                "size": EXPECTED_APK_SIZE,
                "sha256": EXPECTED_APK_SHA256,
            },
            "source_pair_receipt": {
                "path": str(args.source_pair_receipt.absolute()),
                "sha256": pair_sha,
            },
            "extraction": {
                "method": "python_zipfile_direct_no_loose_fallback",
                "output_root": str(output_root),
                "command_argv": [str(Path(__file__).absolute()), *os.sys.argv[1:]],
                "exit_code": 0,
                "inspection_tool": {
                    "logical_path": str(readelf),
                    "resolved_path": str(resolved_readelf),
                    "resolved_sha256": readelf_sha,
                },
            },
            "device_verified": False,
            "engine_started": False,
            "artifacts": artifacts,
        }
        receipt_path = output_root / "native-bundle.json"
        temporary = output_root / f".native-bundle.json.tmp.{os.getpid()}"
        temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, receipt_path)
        print(
            f"UNITY_APK_BINARY_ONLY_EXTRACT_PASS generation={generation_id} "
            f"apk_sha256={EXPECTED_APK_SHA256} artifacts={len(artifacts)} receipt={receipt_path}"
        )
        return 0
    except Exception:
        if created:
            shutil.rmtree(output_root, ignore_errors=True)
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Reject, zipfile.BadZipFile, OSError) as exc:
        print(f"UNITY_APK_BINARY_ONLY_EXTRACT_REJECT {exc}", file=os.sys.stderr)
        raise SystemExit(1)
