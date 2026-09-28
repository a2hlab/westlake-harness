#!/usr/bin/env python3
"""Create a fail-closed identity receipt for one runtime generation and Unity bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path, PurePosixPath


GEN_SCHEMA = "westlake.l03_a12.provider_closure.v3"
CARD_SCHEMA = "westlake.cardwords.native_bundle.v1"
OUT_SCHEMA = "westlake.unity.generation_private_identity.v1"
SHA256_RE = re.compile(r"[0-9a-f]{64}")
BUILD_ID_RE = re.compile(r"(?:[0-9a-f]{2}){8,64}")
GEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class Reject(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        raise Reject(f"{label} must be a non-symlink directory: {path}")


def safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise Reject(f"unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise Reject(f"unsafe relative path: {value!r}")
    return value


def below(root: Path, relative: object, label: str) -> Path:
    value = safe_relative(relative)
    current = root
    for part in PurePosixPath(value).parts:
        current = current / part
        if current.is_symlink():
            raise Reject(f"{label} path contains symlink: {value}")
    regular(current, label)
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise Reject(f"{label} escapes its private root: {value}") from exc
    return current


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
    program = run(readelf, path, "--program-headers", "--wide")
    elf64 = "ELF64" in header or "Class: 64-bit" in header
    aarch64 = "AArch64" in header or "AARCH64" in header or "aarch64" in header
    if not elf64 or not aarch64:
        raise Reject(f"artifact is not ELF64/AArch64: {path}")
    build_ids = [value.lower() for value in re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)]
    if len(build_ids) != 1 or BUILD_ID_RE.fullmatch(build_ids[0]) is None:
        raise Reject(f"artifact requires one exact 8-64-byte Build-ID: {path}")
    sonames = re.findall(r"(?:\(SONAME\)|\bSONAME\b).*?\[([^]]+)\]", dynamic)
    if len(sonames) > 1:
        raise Reject(f"artifact has ambiguous SONAME: {path}")
    needed = re.findall(r"(?:\(NEEDED\)|\bNEEDED\b).*?\[([^]]+)\]", dynamic)
    interps = re.findall(r"Requesting program interpreter:\s*([^]]+)\]", program)
    if len(interps) > 1:
        raise Reject(f"artifact has ambiguous PT_INTERP: {path}")
    return {
        "sha256": sha256(path),
        "build_id": build_ids[0],
        "soname": sonames[0] if sonames else None,
        "dt_needed": needed,
        "pt_interp": interps[0] if interps else None,
    }


def exact_digest(expected: object, actual: str, label: str) -> None:
    if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None:
        raise Reject(f"{label} has invalid expected SHA256")
    if expected != actual:
        raise Reject(f"{label} SHA256 mismatch: expected={expected} actual={actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-root", required=True, type=Path)
    parser.add_argument("--generation-manifest", required=True, type=Path)
    parser.add_argument("--cardwords-root", required=True, type=Path)
    parser.add_argument("--cardwords-receipt", required=True, type=Path)
    parser.add_argument("--readelf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    gen_root = args.generation_root.absolute()
    card_root = args.cardwords_root.absolute()
    directory(gen_root, "generation root")
    directory(card_root, "CardWords root")
    regular(args.readelf, "readelf")
    if not os.access(args.readelf, os.X_OK):
        raise Reject("readelf is not executable")
    expected_manifest = gen_root / "meta/generation.json"
    if args.generation_manifest.absolute() != expected_manifest:
        raise Reject("generation manifest must be GENERATION_ROOT/meta/generation.json")
    expected_card_receipt = card_root / "native-bundle.json"
    if args.cardwords_receipt.absolute() != expected_card_receipt:
        raise Reject("CardWords receipt must be CARDWORDS_ROOT/native-bundle.json")
    if (gen_root / "meta/INCOMPLETE").exists():
        raise Reject("generation is incomplete")
    generation = load_json(expected_manifest, "generation manifest")
    card = load_json(expected_card_receipt, "CardWords receipt")
    if generation.get("schema") != GEN_SCHEMA:
        raise Reject(f"wrong generation schema: {generation.get('schema')}")
    generation_id = generation.get("generation_id")
    if not isinstance(generation_id, str) or GEN_RE.fullmatch(generation_id) is None:
        raise Reject("invalid generation_id")
    if gen_root.name != generation_id:
        raise Reject("generation root basename differs from generation_id")
    if card.get("schema") != CARD_SCHEMA:
        raise Reject(f"wrong CardWords schema: {card.get('schema')}")
    manifest_sha = sha256(expected_manifest)
    token = f"wlgen-{generation_id}-{manifest_sha}"
    if card.get("generation_id") != generation_id:
        raise Reject("mixed generation: CardWords receipt generation_id differs")
    if card.get("generation_manifest_sha256") != manifest_sha:
        raise Reject("mixed generation: CardWords receipt manifest SHA256 differs")
    if card.get("generation_token") != token:
        raise Reject("mixed generation: CardWords receipt generation token differs")
    artifacts: list[dict] = []
    seen_roles: set[str] = set()
    gen_records = generation.get("artifacts")
    if not isinstance(gen_records, list) or not gen_records:
        raise Reject("generation artifacts are missing")
    for item in gen_records:
        if not isinstance(item, dict) or not isinstance(item.get("role"), str):
            raise Reject("malformed generation artifact")
        role = f"generation:{item['role']}"
        if role in seen_roles:
            raise Reject(f"duplicate role: {role}")
        seen_roles.add(role)
        path = below(gen_root / "payload", item.get("path"), role)
        identity = inspect(args.readelf, path)
        exact_digest(item.get("sha256"), identity["sha256"], role)
        artifacts.append({"role": role, "root": "generation", "path": item["path"], **identity})

    card_records = card.get("artifacts")
    if not isinstance(card_records, list):
        raise Reject("CardWords artifacts are missing")
    card_roles: set[str] = set()
    required_card_roles = {
        "libmain", "libunity", "libil2cpp", "lib_burst_generated",
    }
    for item in card_records:
        if not isinstance(item, dict) or item.get("role") not in required_card_roles:
            raise Reject("CardWords receipt contains an unsupported native DSO role")
        raw_role = item["role"]
        if raw_role in card_roles:
            raise Reject(f"duplicate CardWords role: {raw_role}")
        card_roles.add(raw_role)
        path = below(card_root, item.get("path"), raw_role)
        identity = inspect(args.readelf, path)
        exact_digest(item.get("sha256"), identity["sha256"], raw_role)
        expected_soname = f"{raw_role}.so"
        if identity["soname"] is not None and identity["soname"] != expected_soname:
            raise Reject(f"{raw_role} SONAME mismatch: {identity['soname']}")
        artifacts.append({"role": f"cardwords:{raw_role}", "root": "cardwords", "path": item["path"], **identity})
    if card_roles != required_card_roles:
        raise Reject(
            "CardWords receipt must exactly cover libmain/libunity/"
            f"libil2cpp/lib_burst_generated: {sorted(card_roles)}"
        )

    receipt = {
        "schema": OUT_SCHEMA,
        "status": "identity_pass",
        "generation_id": generation_id,
        "generation_token": token,
        "roots": {
            "generation": str(gen_root),
            "cardwords": str(card_root),
        },
        "generation_manifest": {"path": "meta/generation.json", "sha256": manifest_sha},
        "cardwords_receipt_sha256": sha256(expected_card_receipt),
        "device_verified": False,
        "engine_started": False,
        "artifacts": artifacts,
    }
    if args.output.exists() or args.output.is_symlink():
        raise Reject(f"refusing output reuse: {args.output}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.output)
    print(f"UNITY_IDENTITY_PASS generation={generation_id} artifacts={len(artifacts)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Reject as exc:
        print(f"UNITY_IDENTITY_REJECT {exc}", file=os.sys.stderr)
        raise SystemExit(1)
