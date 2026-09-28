#!/usr/bin/env python3
"""Verify the full L03.A12 payload + immutable-base ELF deploy closure.

This gate is intentionally independent from the NativeLoader contract gate.
It never loads target ELFs; it hashes and inspects them with llvm-readelf.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath


SCHEMA = "westlake.l03_a12.provider_closure.v3"
SHA256 = re.compile(r"[0-9a-f]{64}")
ROLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
EXPECTED_ROLES = {
    "backend",
    "bridge",
    "native_loader",
    "runtime",
    "profile",
    "unwindstack",
    "art",
    "appspawn",
    "oh_service",
}
PROFILE_B_SYMBOLS = {
    "OpenNativeLibrary",
    "CloseNativeLibrary",
    "NativeLoaderFreeErrorMessage",
    "InitializeNativeLoader",
    "ResetNativeLoader",
    "CreateClassLoaderNamespace",
}
ANL_SYMBOLS = {
    "ANL_CreateDomain",
    "ANL_Dlopen",
    "ANL_Dlclose",
    "ANL_Dlerror",
    "ANL_ReleaseDomainHandle",
}
LEGACY_SYMBOLS = {
    "_ZN7android17OpenNativeLibraryEP7_JNIEnviPKcP8_jobjectS3_P8_jstringPbPPc",
    "_ZN7android18CloseNativeLibraryEPvbPPc",
    "_ZN7android28NativeLoaderFreeErrorMessageEPc",
    "_ZN7android22InitializeNativeLoaderEv",
    "_ZN7android17ResetNativeLoaderEv",
    "_ZN7android26CreateClassLoaderNamespaceEP7_JNIEnviP8_jobjectbP8_jstringS5_S5_S5_",
    "FindNativeLoaderNamespaceByClassLoader",
    "FindSymbolInNativeLoaderNamespace",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    if any(character in value for character in ("\t", "\n", "\r")):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(part not in ("", ".", "..") for part in path.parts)


def path_has_symlink(root: Path, relative: str) -> bool:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def exact_regular_files(root: Path) -> tuple[set[str], list[tuple[str, str]]]:
    paths: set[str] = set()
    errors: list[tuple[str, str]] = []
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in list(dirnames):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                errors.append(("closure_symlink", relative))
                dirnames.remove(name)
        for name in filenames:
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                errors.append(("closure_stat", f"path={relative} error={exc}"))
                continue
            if stat.S_ISLNK(mode):
                errors.append(("closure_symlink", relative))
            elif stat.S_ISREG(mode):
                paths.add(relative)
            else:
                errors.append(("closure_not_regular", relative))
    return paths, errors


class Gate:
    def __init__(self) -> None:
        self.checks = 0
        self.failures = 0

    def ok(self, code: str, detail: str) -> None:
        self.checks += 1
        print(f"DEPLOY_CLOSURE_OK code={code} detail={detail}")

    def fail(self, code: str, detail: object) -> None:
        self.checks += 1
        self.failures += 1
        clean = str(detail).replace("\n", " ").replace("\r", " ")
        print(f"DEPLOY_CLOSURE_FAIL code={code} detail={clean}", file=sys.stderr)


def readelf(readelf_path: str, path: Path, *arguments: str) -> tuple[bool, str]:
    result = subprocess.run(
        [readelf_path, *arguments, str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode == 0, result.stdout


def dynsym_rows(text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in text.splitlines():
        fields = raw.split()
        if len(fields) < 8 or not fields[0].endswith(":") or not fields[0][:-1].isdigit():
            continue
        rows.append(
            {
                "type": fields[3],
                "bind": fields[4],
                "visibility": fields[5],
                "index": fields[6],
                "name": fields[7].split("@", 1)[0],
            }
        )
    return rows


def validate_record(
    gate: Gate,
    item: object,
    index: int,
    scope: str,
    root: Path,
    seen_roles: set[str],
    seen_paths: set[str],
) -> dict[str, object] | None:
    if not isinstance(item, dict):
        gate.fail("closure_record", f"scope={scope} index={index}")
        return None
    role = item.get("role")
    relative = item.get("path")
    digest = item.get("sha256")
    if not isinstance(role, str) or ROLE.fullmatch(role) is None:
        gate.fail("closure_role", f"scope={scope} role={role}")
        return None
    if role in seen_roles:
        gate.fail("duplicate_role", f"scope={scope} role={role}")
    seen_roles.add(role)
    if not safe_relative(relative):
        gate.fail("closure_path", f"scope={scope} path={relative}")
        return None
    assert isinstance(relative, str)
    if relative in seen_paths:
        gate.fail("duplicate_path", f"scope={scope} path={relative}")
    seen_paths.add(relative)
    if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
        gate.fail("closure_digest", f"scope={scope} path={relative}")
    path = root.joinpath(*PurePosixPath(relative).parts)
    if path_has_symlink(root, relative):
        gate.fail("closure_symlink", f"scope={scope} path={relative}")
    elif not path.is_file():
        gate.fail("closure_missing", f"scope={scope} path={relative}")
    else:
        actual = sha256(path)
        if actual == digest:
            gate.ok("closure_hash", f"scope={scope} role={role} path={relative}")
        else:
            gate.fail(
                "hash_mismatch",
                f"scope={scope} role={role} path={relative} expected={digest} actual={actual}",
            )
    record: dict[str, object] = {
        "scope": scope,
        "role": role,
        "relative": relative,
        "path": path,
        "sha256": digest,
    }
    if scope == "base":
        deploy_path = item.get("deploy_path")
        if (
            not isinstance(deploy_path, str)
            or not deploy_path.startswith("/")
            or ".." in PurePosixPath(deploy_path).parts
        ):
            gate.fail("base_deploy_path", f"role={role} path={deploy_path}")
        record["deploy_path"] = deploy_path
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("payload_root")
    parser.add_argument("--readelf", required=True)
    args = parser.parse_args()

    gate = Gate()
    manifest_path = Path(args.manifest).absolute()
    payload_root = Path(args.payload_root).absolute()
    generation = "unknown"

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        gate.fail("manifest_parse", exc)
        data = {}

    if not isinstance(data, dict):
        gate.fail("manifest_root", type(data).__name__)
        data = {}
    generation_value = data.get("generation_id")
    if isinstance(generation_value, str):
        generation = generation_value
    if data.get("schema") != SCHEMA:
        gate.fail("manifest_schema", data.get("schema"))

    closure = data.get("closure")
    if not isinstance(closure, dict):
        gate.fail("closure_contract", type(closure).__name__)
        closure = {}
    if closure.get("provider_subgraph_scope") != "payload":
        gate.fail("provider_subgraph_scope", closure.get("provider_subgraph_scope"))
    if closure.get("deploy_closure_scope") != "payload+immutable_base":
        gate.fail("deploy_closure_scope", closure.get("deploy_closure_scope"))
    expected_interp = closure.get("expected_interpreter")
    if not isinstance(expected_interp, str) or not expected_interp.startswith("/"):
        gate.fail("expected_interpreter", expected_interp)

    base = data.get("immutable_base")
    if not isinstance(base, dict):
        gate.fail("immutable_base", type(base).__name__)
        base = {}
    base_relative = base.get("root")
    if not safe_relative(base_relative):
        gate.fail("immutable_base_root", base_relative)
        base_root = manifest_path.parent / "invalid-base-root"
    else:
        assert isinstance(base_relative, str)
        base_root = manifest_path.parent.joinpath(*PurePosixPath(base_relative).parts)
    if path_has_symlink(manifest_path.parent, base_relative) if isinstance(base_relative, str) else False:
        gate.fail("immutable_base_symlink", base_relative)
    if not base_root.is_dir():
        gate.fail("immutable_base_missing", base_root)
    image_fingerprint = base.get("image_fingerprint")
    if not isinstance(image_fingerprint, str) or not image_fingerprint.strip():
        gate.fail("image_fingerprint", image_fingerprint)

    payload_items = data.get("artifacts")
    if not isinstance(payload_items, list):
        gate.fail("artifacts_missing", type(payload_items).__name__)
        payload_items = []
    base_items = base.get("artifacts")
    if not isinstance(base_items, list):
        gate.fail("base_artifacts_missing", type(base_items).__name__)
        base_items = []

    records: list[dict[str, object]] = []
    payload_roles: set[str] = set()
    payload_paths: set[str] = set()
    for index, item in enumerate(payload_items):
        if isinstance(item, dict) and (
            item.get("role") == "runtime_stubs"
            or item.get("path") == "aosp/libart_runtime_stubs.so"
        ):
            gate.fail("forbidden_broad_runtime_stub", str(item.get("path")))
        record = validate_record(
            gate, item, index, "payload", payload_root, payload_roles, payload_paths
        )
        if record is not None:
            records.append(record)
    for role in sorted(EXPECTED_ROLES - payload_roles):
        gate.fail("required_role", role)

    base_roles: set[str] = set()
    base_paths: set[str] = set()
    for index, item in enumerate(base_items):
        record = validate_record(
            gate, item, index, "base", base_root, base_roles, base_paths
        )
        if record is not None:
            records.append(record)
    if "loader" not in base_roles:
        gate.fail("required_base_role", "loader")

    for scope, root, expected_paths in (
        ("payload", payload_root, payload_paths),
        ("base", base_root, base_paths),
    ):
        if root.is_dir():
            actual_paths, errors = exact_regular_files(root)
            for code, detail in errors:
                gate.fail(code, f"scope={scope} path={detail}")
            for relative in sorted(expected_paths - actual_paths):
                gate.fail("closure_missing", f"scope={scope} path={relative}")
            for relative in sorted(actual_paths - expected_paths):
                gate.fail("closure_stale_extra", f"scope={scope} path={relative}")
            if actual_paths == expected_paths:
                gate.ok("closure_exact", f"scope={scope} files={len(actual_paths)}")

    deployment = data.get("deployment")
    if not isinstance(deployment, dict):
        gate.fail("deploy_plan", type(deployment).__name__)
        deployment = {}
    if deployment.get("schema") != "westlake.l03_a12.deploy_plan.v1":
        gate.fail("deploy_plan_schema", deployment.get("schema"))
    if deployment.get("generation_id") != generation:
        gate.fail("deploy_generation", deployment.get("generation_id"))
    if deployment.get("image_fingerprint") != image_fingerprint:
        gate.fail("deploy_image_fingerprint", deployment.get("image_fingerprint"))
    if deployment.get("filesystem_type") != "ext4":
        gate.fail("deploy_filesystem", deployment.get("filesystem_type"))
    if deployment.get("expected_interpreter") != expected_interp:
        gate.fail("deploy_interpreter", deployment.get("expected_interpreter"))
    entries = deployment.get("entries")
    if not isinstance(entries, list):
        gate.fail("deploy_entries", type(entries).__name__)
        entries = []
    entry_sources: set[str] = set()
    destinations: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            gate.fail("deploy_entry", index)
            continue
        source = entry.get("source")
        destination = entry.get("destination")
        if not safe_relative(source):
            gate.fail("deploy_source", source)
        elif source in entry_sources:
            gate.fail("deploy_source_duplicate", source)
        else:
            entry_sources.add(source)
        if (
            not isinstance(destination, str)
            or not destination.startswith("/")
            or ".." in PurePosixPath(destination).parts
        ):
            gate.fail("deploy_destination", destination)
        elif destination in destinations:
            gate.fail("deploy_destination_duplicate", destination)
        else:
            destinations.add(destination)
        for field in ("owner", "group", "selinux_label", "namespace_owner"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                gate.fail("deploy_metadata", f"index={index} field={field}")
        if not isinstance(entry.get("mode"), str) or re.fullmatch(r"0[0-7]{3}", entry["mode"]) is None:
            gate.fail("deploy_mode", f"index={index} mode={entry.get('mode')}")
    if entry_sources != payload_paths:
        gate.fail(
            "deploy_payload_coverage",
            f"missing={sorted(payload_paths - entry_sources)} extra={sorted(entry_sources - payload_paths)}",
        )
    else:
        gate.ok("deploy_payload_coverage", f"files={len(payload_paths)}")

    providers: dict[str, list[dict[str, object]]] = {}
    symbol_definitions: dict[str, list[tuple[dict[str, object], dict[str, str]]]] = {}
    appspawn_records: list[dict[str, object]] = []

    for record in records:
        path = record["path"]
        assert isinstance(path, Path)
        role = str(record["role"])
        scope = str(record["scope"])
        relative = str(record["relative"])
        label = f"scope={scope} role={role} path={relative}"
        if not path.is_file() or path.is_symlink():
            continue

        header_ok, header = readelf(args.readelf, path, "-h", "--wide")
        if not header_ok:
            gate.fail("elf_header", label)
            continue
        if re.search(r"Class:\s+ELF64", header):
            gate.ok("elf_class", label)
        else:
            gate.fail("wrong_class", label)
        if re.search(r"Machine:\s+AArch64", header):
            gate.ok("elf_machine", label)
        else:
            gate.fail("wrong_machine", label)
        elf_type_match = re.search(r"Type:\s+([A-Z]+)", header)
        elf_type = elf_type_match.group(1) if elf_type_match else "unknown"
        if (role == "appspawn" and elf_type in {"DYN", "EXEC"}) or (
            role != "appspawn" and elf_type == "DYN"
        ):
            gate.ok("elf_type", f"{label} type={elf_type}")
        else:
            gate.fail("elf_type", f"{label} type={elf_type}")

        _, dynamic = readelf(args.readelf, path, "-d", "--wide")
        _, program = readelf(args.readelf, path, "-l", "--wide")
        _, notes = readelf(args.readelf, path, "-n", "--wide")
        _, symbols = readelf(args.readelf, path, "--dyn-syms", "--wide")
        sonames = re.findall(r"Library soname:\s*\[([^]]+)\]", dynamic)
        needed = re.findall(r"Shared library:\s*\[([^]]+)\]", dynamic)
        interpreters = re.findall(r"Requesting program interpreter:\s*([^]]+)\]", program)
        # The immutable base is copied byte-for-byte from the image-matched
        # OpenHarmony official prebuilt set.  Its admission identity is the
        # pinned image fingerprint + manifest SHA, not adapter-produced ELF
        # policy.  Preserve and report the vendor ELF metadata without asking
        # it to satisfy the stricter build-id/dynamic-tag rules that apply to
        # generation-produced payloads.
        if scope == "base":
            build_id = re.search(r"Build ID:\s*([0-9a-fA-F]+)", notes)
            dynamic_tags = re.findall(r"\((RPATH|RUNPATH|TEXTREL)\)", dynamic)
            gate.ok(
                "official_prebuilt_trusted",
                f"{label} build_id={build_id.group(1) if build_id else 'NONE'} "
                f"recorded_dynamic_tags={','.join(dynamic_tags) if dynamic_tags else 'NONE'}",
            )
        else:
            if re.search(r"Build ID:\s*[0-9a-fA-F]+", notes):
                gate.ok("build_id", label)
            else:
                gate.fail("build_id", label)
            if re.search(r"\((?:RPATH|RUNPATH|TEXTREL)\)", dynamic):
                gate.fail("unsafe_dynamic_tag", label)
            else:
                gate.ok("unsafe_dynamic_tag_absent", label)

        if role == "appspawn":
            appspawn_records.append(record)
            if interpreters == [expected_interp]:
                gate.ok("pt_interp", f"{label} interpreter={expected_interp}")
            else:
                gate.fail(
                    "wrong_pt_interp",
                    f"{label} expected={expected_interp} actual={interpreters}",
                )
        else:
            # Musl's dynamic loader is also the libc provider and therefore
            # intentionally advertises SONAME libc.so even when installed as
            # ld-musl-aarch64.so.1.
            expected_soname = "libc.so" if role == "loader" else path.name
            if sonames == [expected_soname]:
                gate.ok("soname", f"{label} soname={expected_soname}")
            elif scope == "base" and not sonames and role != "loader":
                gate.ok(
                    "filename_provider",
                    f"{label} basename={path.name} soname=absent",
                )
            else:
                gate.fail("soname", f"{label} expected={expected_soname} actual={sonames}")
            provider_names = sonames
            if scope == "base" and not sonames and role != "loader":
                provider_names = [path.name]
            for soname in provider_names:
                providers.setdefault(soname, []).append(record)

        record["needed"] = needed
        for row in dynsym_rows(symbols):
            if row["index"] != "UND":
                symbol_definitions.setdefault(row["name"], []).append((record, row))

    if len(appspawn_records) != 1:
        gate.fail("appspawn_cardinality", len(appspawn_records))

    loader_matches = [
        record
        for record in records
        if record.get("scope") == "base"
        and record.get("role") == "loader"
        and record.get("deploy_path") == expected_interp
    ]
    if len(loader_matches) == 1:
        gate.ok("interpreter_provider", f"path={expected_interp}")
    else:
        gate.fail("interpreter_provider", f"path={expected_interp} count={len(loader_matches)}")

    for record in records:
        for soname in record.get("needed", []):
            matches = providers.get(str(soname), [])
            consumer = f"scope={record['scope']} role={record['role']} path={record['relative']}"
            if len(matches) == 1:
                provider = matches[0]
                gate.ok(
                    "needed_resolved",
                    f"{consumer} needed={soname} provider={provider['scope']}:{provider['relative']}",
                )
            elif not matches:
                gate.fail("unresolved_needed", f"{consumer} needed={soname}")
            else:
                owners = ",".join(
                    f"{item['scope']}:{item['relative']}" for item in matches
                )
                gate.fail(
                    "ambiguous_needed_provider",
                    f"{consumer} needed={soname} providers={owners}",
                )

    def require_owner(symbols: set[str], role: str, code: str) -> None:
        for symbol in sorted(symbols):
            definitions = symbol_definitions.get(symbol, [])
            strong = [
                item
                for item in definitions
                if item[1]["type"] == "FUNC"
                and item[1]["bind"] == "GLOBAL"
                and item[1]["visibility"] == "DEFAULT"
            ]
            weak = [item for item in definitions if item[1]["bind"] == "WEAK"]
            owners = [str(item[0]["role"]) for item in strong]
            if len(definitions) == 1 and len(strong) == 1 and owners == [role]:
                gate.ok(code, f"symbol={symbol} role={role}")
            else:
                gate.fail(
                    "provider_cardinality",
                    f"symbol={symbol} definitions={len(definitions)} strong={len(strong)} owners={owners}",
                )
            if weak:
                gate.fail(
                    "weak_native_loader_symbol",
                    f"symbol={symbol} rows={len(weak)}",
                )

    require_owner(PROFILE_B_SYMBOLS, "native_loader", "native_loader_provider")
    require_owner(ANL_SYMBOLS, "backend", "backend_provider")
    for symbol in sorted(LEGACY_SYMBOLS):
        definitions = symbol_definitions.get(symbol, [])
        if definitions:
            gate.fail("legacy_provider", f"symbol={symbol} definitions={len(definitions)}")
        else:
            gate.ok("legacy_provider_absent", f"symbol={symbol}")

    for record in records:
        path = record["path"]
        assert isinstance(path, Path)
        expected = str(record["sha256"])
        if path.is_file() and not path.is_symlink() and sha256(path) == expected:
            gate.ok(
                "closure_stable",
                f"scope={record['scope']} role={record['role']} path={record['relative']}",
            )
        else:
            gate.fail(
                "closure_changed",
                f"scope={record['scope']} role={record['role']} path={record['relative']}",
            )

    print(f"DEPLOY_CLOSURE_SUMMARY checks={gate.checks} failures={gate.failures}")
    if gate.failures:
        print(f"DEPLOY_CLOSURE_REJECT generation={generation}", file=sys.stderr)
        return 1
    print(f"DEPLOY_CLOSURE_PASS generation={generation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
