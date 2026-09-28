#!/usr/bin/env python3
"""Verify an exact Route-A/runtime generation without trusting build claims.

The verifier is deliberately independent of the product build scripts.  It
accepts explicit project/source/build roots and a byte-pinned candidate
manifest, then re-derives the properties needed before a generation may be
offered to a device owner.  It never edits product sources or artifacts.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "westlake.runtime-generation-candidate.v1"
REPORT_SCHEMA = "westlake.runtime-generation-verdict.v1"
LINK_SCHEMA = "westlake.link-argv.v1"
TOKEN_SECTION = ".westlake_generation"
TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]{7,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA1_BUILD_ID_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_DYNAMIC_ROOTS = {"android_runtime", "adapter_bridge"}
REQUIRED_SOURCE_CONTRACTS = {
    "runtime_root_failure",
    "startreg_failure",
    "preload_throwable_failure",
}


class GateError(RuntimeError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_digest(entries: Iterable[tuple[str, str]]) -> str:
    material = "".join(f"{digest}  {relative}\n" for relative, digest in sorted(entries))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def validate_relative(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise GateError("manifest_shape", f"{field} must be a non-empty relative path")
    path = Path(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise GateError("path_escape", f"{field} is not a canonical relative path: {value!r}")
    return path


def require_regular_under(root: Path, relative: Any, *, field: str) -> Path:
    rel = validate_relative(relative, field=field)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            stat = current.lstat()
        except FileNotFoundError as exc:
            raise GateError("missing_input", f"{field} does not exist: {current}") from exc
        if os.path.islink(current):
            raise GateError("symlink_input", f"{field} traverses a symlink: {current}")
    resolved = current.resolve()
    if not is_relative_to(resolved, root):
        raise GateError("path_escape", f"{field} escaped {root}: {resolved}")
    if not current.is_file():
        raise GateError("missing_input", f"{field} is not a regular file: {current}")
    return current


def require_directory_under(root: Path, relative: Any, *, field: str) -> Path:
    rel = validate_relative(relative, field=field)
    current = root
    for part in rel.parts:
        current = current / part
        try:
            current.lstat()
        except FileNotFoundError as exc:
            raise GateError("missing_input", f"{field} does not exist: {current}") from exc
        if os.path.islink(current):
            raise GateError("symlink_input", f"{field} traverses a symlink: {current}")
    resolved = current.resolve()
    if not is_relative_to(resolved, root) or not current.is_dir():
        raise GateError("path_escape", f"{field} is not a project-local directory: {current}")
    return current


def run(tool: Path, *argv: str) -> str:
    result = subprocess.run(
        [str(tool), *argv],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        raise GateError("readelf_failed", f"{' '.join(argv)} failed: {result.stdout.strip()}")
    return result.stdout


def normalize_symbol(name: str) -> str:
    return name.split("@", 1)[0]


@dataclasses.dataclass(frozen=True)
class ElfInfo:
    path: Path
    elf_class: str
    machine: str
    elf_type: str
    soname: str | None
    build_id: str | None
    needed: tuple[str, ...]
    unsafe_tags: tuple[str, ...]
    generation_tokens: tuple[str, ...]
    strong_undefined: frozenset[str]
    strong_defined: frozenset[str]


def inspect_elf(readelf: Path, path: Path) -> ElfInfo:
    header = run(readelf, "--file-header", "--wide", str(path))
    dynamic = run(readelf, "--dynamic", "--wide", str(path))
    notes = run(readelf, "--notes", "--wide", str(path))
    symbols = run(readelf, "--dyn-syms", "--wide", str(path))
    strings = run(readelf, f"--string-dump={TOKEN_SECTION}", str(path))

    class_match = re.search(r"Class:\s*(ELF\d+)", header)
    machine_match = re.search(r"Machine:\s*(.+)", header)
    type_match = re.search(r"Type:\s*([A-Z]+)", header)
    if not class_match or not machine_match or not type_match:
        raise GateError("elf_header", f"incomplete ELF header: {path}")
    sonames = re.findall(r"\(SONAME\).*?\[([^]]+)\]", dynamic)
    if len(sonames) > 1:
        raise GateError("soname", f"multiple SONAME entries: {path}")
    build_ids = re.findall(r"Build ID:\s*([0-9a-fA-F]+)", notes)
    if len(build_ids) > 1:
        raise GateError("build_id", f"multiple GNU Build-IDs: {path}")
    needed = tuple(re.findall(r"\(NEEDED\).*?\[([^]]+)\]", dynamic))
    unsafe = tuple(
        sorted(set(re.findall(r"\((RPATH|RUNPATH|TEXTREL)\)", dynamic)))
    )
    tokens = tuple(
        value.strip()
        for value in re.findall(r"^\s*\[\s*[0-9a-fA-F]+\]\s+(.+?)\s*$", strings, re.M)
        if value.strip()
    )

    undefined: set[str] = set()
    defined: set[str] = set()
    symbol_re = re.compile(
        r"^\s*\d+:\s+\S+\s+\d+\s+\S+\s+(GLOBAL|WEAK)\s+(\S+)\s+(\S+)\s+(.+?)\s*$"
    )
    for line in symbols.splitlines():
        match = symbol_re.match(line)
        if not match:
            continue
        binding, visibility, index, raw_name = match.groups()
        name = normalize_symbol(raw_name.strip())
        if not name:
            continue
        if index == "UND" and binding == "GLOBAL":
            undefined.add(name)
        elif (
            index != "UND"
            and binding == "GLOBAL"
            and visibility in ("DEFAULT", "PROTECTED")
        ):
            defined.add(name)
    return ElfInfo(
        path=path,
        elf_class=class_match.group(1),
        machine=machine_match.group(1).strip(),
        elf_type=type_match.group(1),
        soname=sonames[0] if sonames else None,
        build_id=build_ids[0].lower() if build_ids else None,
        needed=needed,
        unsafe_tags=unsafe,
        generation_tokens=tokens,
        strong_undefined=frozenset(undefined),
        strong_defined=frozenset(defined),
    )


def find_function(text: str, anchor: str) -> str:
    if not isinstance(anchor, str) or not anchor:
        raise GateError("manifest_shape", "function_anchor must be a non-empty string")
    if text.count(anchor) != 1:
        raise GateError("source_callsite", f"function anchor must occur once: {anchor!r}")
    start = text.index(anchor)
    opening = text.find("{", start + len(anchor))
    if opening < 0:
        raise GateError("source_callsite", f"function has no body: {anchor!r}")
    depth = 0
    state = "code"
    quote = ""
    escaped = False
    index = opening
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "line_comment":
            if char == "\n":
                state = "code"
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                state = "code"
                index += 1
        elif state == "string":
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                state = "code"
        else:
            if char == "/" and nxt == "/":
                state = "line_comment"
                index += 1
            elif char == "/" and nxt == "*":
                state = "block_comment"
                index += 1
            elif char in ('"', "'"):
                state = "string"
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        index += 1
    raise GateError("source_callsite", f"unbalanced function body: {anchor!r}")


def find_branch(function: str, condition_pattern: str, *, label: str) -> str:
    match = re.search(condition_pattern, function)
    if not match:
        raise GateError("failure_contract", f"missing {label} failure branch")
    opening = function.find("{", match.end())
    if opening < 0:
        raise GateError("failure_contract", f"{label} branch has no compound body")
    depth = 0
    for index in range(opening, len(function)):
        if function[index] == "{":
            depth += 1
        elif function[index] == "}":
            depth -= 1
            if depth == 0:
                return function[opening + 1 : index]
    raise GateError("failure_contract", f"unbalanced {label} failure branch")


def require_nonzero_return(branch: str, *, label: str, code: str) -> None:
    returns = [value.strip() for value in re.findall(r"\breturn\s+([^;]+);", branch)]
    if not returns:
        raise GateError(code, f"{label} branch has no explicit failure return")
    success_values = {"0", "false", "nullptr", "NULL", "EXIT_SUCCESS"}
    if any(value.strip("() ") in success_values for value in returns):
        raise GateError(code, f"{label} branch can return success: {returns}")


def canonical_stat(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "dev": int(stat.st_dev),
        "ino": int(stat.st_ino),
        "size": int(stat.st_size),
        "sha256": sha256(path),
    }


def path_values_from_argv(argv: list[str]) -> list[Path]:
    paths: list[Path] = []
    prefixes = ("--sysroot=", "-I", "-L", "-B", "--version-script=")
    for token in argv:
        candidates = [token]
        if token.startswith("-Wl,"):
            candidates = token[4:].split(",")
        for candidate in candidates:
            value = candidate
            for prefix in prefixes:
                if value.startswith(prefix) and len(value) > len(prefix):
                    value = value[len(prefix) :]
                    break
            paths.append(Path(value))
    return paths


def absolute_paths_from_argv(argv: list[str]) -> list[Path]:
    return [path for path in path_values_from_argv(argv) if path.is_absolute()]


class Verifier:
    def __init__(
        self,
        *,
        project_root: Path,
        source_root: Path,
        build_root: Path,
        manifest_path: Path,
        readelf: Path,
    ) -> None:
        self.project_root = project_root.resolve()
        self.source_root = source_root.resolve()
        self.build_root = build_root.resolve()
        self.manifest_path = manifest_path.resolve()
        # Keep argv[0] as llvm-readelf.  OH SDK ships it as an llvm-readobj
        # symlink and the multicall binary changes its CLI/output by argv[0].
        self.readelf = Path(os.path.abspath(readelf))
        self.manifest: dict[str, Any] = {}
        self.checks: list[dict[str, str]] = []
        self.observed: dict[Path, str] = {}
        self.source_files: dict[str, Path] = {}
        self.source_hashes: dict[str, str] = {}
        self.artifacts: dict[str, dict[str, Any]] = {}
        self.elf: dict[str, ElfInfo] = {}
        self.namespaces: dict[str, dict[str, Any]] = {}

    def pass_gate(self, gate: str, detail: str) -> None:
        self.checks.append({"gate": gate, "status": "PASS", "detail": detail})

    def observe(self, path: Path, expected: str | None = None, *, label: str) -> str:
        actual = sha256(path)
        if expected is not None:
            if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
                raise GateError("manifest_shape", f"invalid SHA256 for {label}")
            if actual != expected:
                raise GateError("hash_drift", f"{label} expected {expected}, got {actual}")
        previous = self.observed.get(path)
        if previous is not None and previous != actual:
            raise GateError("input_changed", f"{label} changed while being inspected")
        self.observed[path] = actual
        return actual

    def validate_roots(self) -> None:
        for label, path in (
            ("source_root", self.source_root),
            ("build_root", self.build_root),
        ):
            if not path.is_dir() or not is_relative_to(path, self.project_root):
                raise GateError("project_root", f"{label} is outside project root: {path}")
        if not self.manifest_path.is_file() or not is_relative_to(
            self.manifest_path, self.build_root
        ):
            raise GateError("manifest_path", "manifest must be a regular file under build_root")
        if not self.readelf.is_file() or not os.access(self.readelf, os.X_OK):
            raise GateError("tool_missing", f"readelf is unavailable: {self.readelf}")

    def load_manifest(self) -> None:
        self.observe(self.manifest_path, label="candidate manifest")
        try:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GateError("manifest_json", str(exc)) from exc
        if not isinstance(value, dict) or value.get("schema") != SCHEMA:
            raise GateError("manifest_schema", f"expected schema {SCHEMA}")
        if value.get("status") != "candidate" or value.get("device_verified") is not False:
            raise GateError("manifest_scope", "candidate must explicitly remain non-device-verified")
        generation_id = value.get("generation_id")
        token = value.get("generation_token")
        if not isinstance(generation_id, str) or not TOKEN_RE.fullmatch(generation_id):
            raise GateError("generation_id", "invalid generation_id")
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            raise GateError("generation_token", "invalid generation_token")
        self.manifest = value
        self.pass_gate("G01_MANIFEST_SCOPE", "schema/status/non-device scope are explicit")

    def validate_source_snapshot(self) -> None:
        snapshot = self.manifest.get("source_snapshot")
        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("files"), list):
            raise GateError("source_snapshot", "source_snapshot.files is required")
        entries: list[tuple[str, str]] = []
        for index, item in enumerate(snapshot["files"]):
            if not isinstance(item, dict):
                raise GateError("source_snapshot", f"source file {index} is not an object")
            relative = item.get("path")
            if relative in self.source_files:
                raise GateError("source_snapshot", f"duplicate source path: {relative}")
            path = require_regular_under(
                self.source_root, relative, field=f"source_snapshot.files[{index}].path"
            )
            digest = self.observe(path, item.get("sha256"), label=f"source {relative}")
            self.source_files[str(relative)] = path
            self.source_hashes[str(relative)] = digest
            entries.append((str(relative), digest))
        expected_digest = snapshot.get("digest")
        actual_digest = tree_digest(entries)
        if expected_digest != actual_digest:
            raise GateError(
                "source_snapshot_digest",
                f"source snapshot digest expected {expected_digest}, got {actual_digest}",
            )
        self.pass_gate("G02_FRESH_SOURCE_BYTES", f"{len(entries)} current source bytes are pinned")

    def validate_namespaces_shape(self) -> None:
        namespaces = self.manifest.get("namespaces")
        if not isinstance(namespaces, list) or not namespaces:
            raise GateError("namespace_shape", "namespaces must be a non-empty list")
        for index, item in enumerate(namespaces):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise GateError("namespace_shape", f"namespace {index} is malformed")
            name = item["id"]
            if name in self.namespaces:
                raise GateError("namespace_shape", f"duplicate namespace: {name}")
            searches = item.get("search_paths")
            imports = item.get("imports")
            if not isinstance(searches, list) or not searches or not isinstance(imports, list):
                raise GateError("namespace_shape", f"namespace {name} needs search_paths/imports")
            search_paths = [
                require_directory_under(
                    self.build_root, relative, field=f"namespace {name} search path"
                )
                for relative in searches
            ]
            if len(set(search_paths)) != len(search_paths):
                raise GateError("namespace_shape", f"namespace {name} repeats a search path")
            self.namespaces[name] = {
                "id": name,
                "search_paths": search_paths,
                "imports": imports,
            }
        for name, item in self.namespaces.items():
            for imported in item["imports"]:
                if imported not in self.namespaces or imported == name:
                    raise GateError("namespace_shape", f"invalid import {name}->{imported}")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visiting:
                raise GateError("namespace_cycle", f"namespace import cycle at {name}")
            if name in visited:
                return
            visiting.add(name)
            for imported in self.namespaces[name]["imports"]:
                visit(imported)
            visiting.remove(name)
            visited.add(name)

        for name in self.namespaces:
            visit(name)

    def validate_artifacts(self) -> None:
        values = self.manifest.get("artifacts")
        if not isinstance(values, list) or not values:
            raise GateError("artifact_shape", "artifacts must be a non-empty list")
        for index, item in enumerate(values):
            if not isinstance(item, dict) or not isinstance(item.get("role"), str):
                raise GateError("artifact_shape", f"artifact {index} is malformed")
            role = item["role"]
            if role in self.artifacts:
                raise GateError("artifact_shape", f"duplicate artifact role: {role}")
            namespace = item.get("namespace")
            if namespace not in self.namespaces:
                raise GateError("artifact_namespace", f"unknown namespace for {role}: {namespace}")
            path = require_regular_under(
                self.build_root, item.get("path"), field=f"artifact {role} path"
            )
            if not any(
                is_relative_to(path.resolve(), search.resolve())
                for search in self.namespaces[namespace]["search_paths"]
            ):
                raise GateError(
                    "artifact_namespace",
                    f"artifact {role} is outside namespace {namespace} search paths",
                )
            digest = self.observe(path, item.get("sha256"), label=f"artifact {role}")
            info = inspect_elf(self.readelf, path)
            if info.elf_class != "ELF64" or "AArch64" not in info.machine:
                raise GateError(
                    "elf64_aarch64",
                    f"{role} is {info.elf_class}/{info.machine}, not ELF64/AArch64",
                )
            kind = item.get("kind")
            if kind == "shared":
                expected_soname = item.get("soname")
                if (
                    not isinstance(expected_soname, str)
                    or info.soname != expected_soname
                    or Path(item["path"]).name != expected_soname
                ):
                    raise GateError(
                        "soname",
                        f"{role} SONAME/path mismatch: expected={expected_soname} actual={info.soname}",
                    )
            elif kind == "executable":
                if info.elf_type not in ("EXEC", "DYN"):
                    raise GateError("elf_type", f"{role} is not an executable ELF")
                if info.soname is not None:
                    raise GateError("soname", f"executable {role} unexpectedly has a SONAME")
            else:
                raise GateError("artifact_shape", f"unsupported kind for {role}: {kind}")
            expected_build_id = item.get("build_id")
            if (
                not isinstance(expected_build_id, str)
                or not SHA1_BUILD_ID_RE.fullmatch(expected_build_id)
                or info.build_id != expected_build_id
            ):
                raise GateError(
                    "build_id",
                    f"{role} requires exact 40-hex GNU Build-ID: expected={expected_build_id} actual={info.build_id}",
                )
            if info.unsafe_tags:
                raise GateError("unsafe_dynamic_tag", f"{role} has {info.unsafe_tags}")
            provenance = item.get("provenance")
            if provenance not in ("generated", "immutable_base"):
                raise GateError("artifact_shape", f"invalid provenance for {role}: {provenance}")
            item = dict(item)
            item["_path"] = path
            item["_sha256"] = digest
            self.artifacts[role] = item
            self.elf[role] = info
        self.pass_gate("G03_ELF64_AARCH64", f"{len(values)} artifacts are ELF64/AArch64")
        self.pass_gate("G04_SONAME", "shared artifacts have exact basename-matching SONAMEs")
        self.pass_gate("G05_BUILD_ID", "all artifacts have exact manifest-bound SHA1 Build-IDs")
        self.pass_gate("G06_NO_RUNPATH_TEXTREL", "RPATH/RUNPATH/TEXTREL are absent")

    def visible_namespaces(self, start: str) -> tuple[str, ...]:
        queue: deque[str] = deque([start])
        result: list[str] = []
        while queue:
            current = queue.popleft()
            if current in result:
                continue
            result.append(current)
            queue.extend(self.namespaces[current]["imports"])
        return tuple(result)

    def candidates_for_soname(self, namespace: str, soname: str) -> list[str]:
        visible = set(self.visible_namespaces(namespace))
        return sorted(
            role
            for role, item in self.artifacts.items()
            if item["namespace"] in visible and self.elf[role].soname == soname
        )

    def source_for_contract(self, contract: dict[str, Any]) -> tuple[Path, str, str]:
        relative = contract.get("source")
        if relative not in self.source_files:
            raise GateError("source_contract", f"contract source is not in snapshot: {relative}")
        expected = contract.get("source_sha256")
        if expected != self.source_hashes[relative]:
            raise GateError("source_contract", f"contract source hash is stale: {relative}")
        path = self.source_files[relative]
        text = path.read_text(encoding="utf-8")
        function = find_function(text, contract.get("function_anchor"))
        return path, text, function

    def validate_dynamic_roots(self) -> None:
        values = self.manifest.get("dynamic_roots")
        if not isinstance(values, list):
            raise GateError("dynamic_root_shape", "dynamic_roots must be a list")
        by_id: dict[str, dict[str, Any]] = {}
        for item in values:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise GateError("dynamic_root_shape", "dynamic root is malformed")
            if item["id"] in by_id:
                raise GateError("dynamic_root_shape", f"duplicate dynamic root: {item['id']}")
            by_id[item["id"]] = item
        if set(by_id) != REQUIRED_DYNAMIC_ROOTS:
            raise GateError(
                "dynamic_root_missing",
                f"required roots={sorted(REQUIRED_DYNAMIC_ROOTS)} actual={sorted(by_id)}",
            )
        for root_id, item in by_id.items():
            caller_role = item.get("caller_role")
            expected_role = item.get("artifact_role")
            namespace = item.get("namespace")
            soname = item.get("soname")
            if caller_role not in self.artifacts or expected_role not in self.artifacts:
                raise GateError("dynamic_root_shape", f"unknown artifact role in {root_id}")
            if namespace not in self.namespaces or self.artifacts[caller_role]["namespace"] != namespace:
                raise GateError("dynamic_root_shape", f"caller namespace mismatch for {root_id}")
            if item.get("failure_contract") != "return_nonzero":
                raise GateError("failure_contract", f"{root_id} lacks return_nonzero contract")
            source_relative = item.get("source")
            if source_relative not in self.source_files:
                raise GateError("dynamic_root_shape", f"source not snapshot-bound: {source_relative}")
            if item.get("source_sha256") != self.source_hashes[source_relative]:
                raise GateError("source_callsite", f"stale source hash for {root_id}")
            function = find_function(
                self.source_files[source_relative].read_text(encoding="utf-8"),
                item.get("function_anchor"),
            )
            try:
                load = list(re.finditer(item.get("load_anchor_regex"), function))
                identity = list(re.finditer(item.get("identity_anchor_regex"), function))
                side_effect = list(re.finditer(item.get("first_side_effect_regex"), function))
            except (TypeError, re.error) as exc:
                raise GateError("dynamic_root_shape", f"invalid callsite regex for {root_id}: {exc}") from exc
            if len(load) != 1 or soname not in load[0].group(0):
                raise GateError("source_callsite", f"{root_id} load callsite is absent/ambiguous")
            if len(identity) != 1 or len(side_effect) != 1:
                raise GateError("identity_timing", f"{root_id} identity/side-effect anchors are ambiguous")
            if not (load[0].start() < identity[0].start() < side_effect[0].start()):
                raise GateError("identity_timing", f"{root_id} identity is not before first side effect")
            variable = item.get("handle_variable")
            if not isinstance(variable, str) or not re.fullmatch(r"[A-Za-z_]\w*", variable):
                raise GateError("dynamic_root_shape", f"invalid handle variable for {root_id}")
            branch = find_branch(
                function,
                rf"\bif\s*\(\s*(?:!\s*{re.escape(variable)}|{re.escape(variable)}\s*==\s*(?:nullptr|NULL|0))\s*\)",
                label=root_id,
            )
            require_nonzero_return(branch, label=root_id, code="dynamic_root_fake_success")
            candidates = self.candidates_for_soname(namespace, soname)
            if candidates != [expected_role]:
                raise GateError(
                    "namespace_reachability",
                    f"{root_id} expected {expected_role}, candidates={candidates}",
                )
            if self.artifacts[expected_role]["provenance"] != "generated":
                raise GateError("dynamic_root_shape", f"dynamic root {expected_role} is not generation-bound")
        self.pass_gate("G07_DYNAMIC_ROOT_MANIFEST", "runtime and bridge roots name caller/callsite/provider")
        self.pass_gate("G08_CALLSITE_FAILURE_CONTRACT", "root failure is nonzero and identity precedes side effects")

    def validate_source_contracts(self) -> None:
        values = self.manifest.get("source_contracts")
        if not isinstance(values, list):
            raise GateError("source_contract", "source_contracts must be a list")
        by_id: dict[str, dict[str, Any]] = {}
        for item in values:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                raise GateError("source_contract", "source contract is malformed")
            if item["id"] in by_id:
                raise GateError("source_contract", f"duplicate source contract: {item['id']}")
            by_id[item["id"]] = item
        if set(by_id) != REQUIRED_SOURCE_CONTRACTS:
            raise GateError(
                "source_contract",
                f"required={sorted(REQUIRED_SOURCE_CONTRACTS)} actual={sorted(by_id)}",
            )

        runtime = by_id["runtime_root_failure"]
        _, _, function = self.source_for_contract(runtime)
        variable = runtime.get("handle_variable")
        branch = find_branch(
            function,
            rf"\bif\s*\(\s*(?:!\s*{re.escape(str(variable))}|{re.escape(str(variable))}\s*==\s*(?:nullptr|NULL|0))\s*\)",
            label="runtime root",
        )
        require_nonzero_return(branch, label="runtime root", code="runtime_fake_success")
        self.pass_gate("G09_RUNTIME_LOAD_FAIL_CLOSED", "missing runtime cannot return success")

        startreg = by_id["startreg_failure"]
        _, _, function = self.source_for_contract(startreg)
        variable = startreg.get("symbol_variable")
        branch = find_branch(
            function,
            rf"\bif\s*\(\s*(?:!\s*{re.escape(str(variable))}|{re.escape(str(variable))}\s*==\s*(?:nullptr|NULL|0))\s*\)",
            label="startReg",
        )
        require_nonzero_return(branch, label="startReg", code="startreg_fake_success")
        if re.search(r"Attempting\s+manual\s+registration|\bregister_android_\w+\s*\(", branch):
            raise GateError("startreg_fallback", "missing startReg enters manual/partial fallback")
        self.pass_gate("G10_STARTREG_FAIL_CLOSED", "missing startReg cannot fall back or return success")

        preload = by_id["preload_throwable_failure"]
        _, _, function = self.source_for_contract(preload)
        branch = find_branch(
            function,
            r"\bif\s*\(\s*(?:\w+\s*->\s*)?ExceptionCheck\s*\(\s*\)\s*\)",
            label="preload Throwable",
        )
        require_nonzero_return(branch, label="preload Throwable", code="preload_fake_success")
        self.pass_gate("G11_PRELOAD_THROWABLE_FAIL_CLOSED", "preload Throwable cannot return success")

    def validate_namespace_closure(self) -> None:
        for role, item in self.artifacts.items():
            namespace = item["namespace"]
            for soname in self.elf[role].needed:
                candidates = self.candidates_for_soname(namespace, soname)
                if not candidates:
                    raise GateError(
                        "namespace_unreachable",
                        f"{role} needs {soname}, but no provider is reachable from {namespace}",
                    )
                if len(candidates) != 1:
                    raise GateError(
                        "soname_ambiguous",
                        f"{role} sees multiple {soname} providers: {candidates}",
                    )
        self.pass_gate("G12_NAMESPACE_REACHABILITY", "every NEEDED edge resolves in its caller namespace")
        self.pass_gate("G13_SONAME_MULTI_CANDIDATE", "disjoint duplicates are allowed; reachable duplicates are rejected")

    def validate_link_receipts(self) -> None:
        token = self.manifest["generation_token"]
        for role, item in self.artifacts.items():
            if item["provenance"] == "immutable_base":
                if item.get("link_receipt") is not None:
                    raise GateError("link_receipt", f"immutable artifact {role} must not claim a current link receipt")
                continue
            receipt_path = require_regular_under(
                self.build_root,
                item.get("link_receipt"),
                field=f"artifact {role} link receipt",
            )
            self.observe(
                receipt_path,
                item.get("link_receipt_sha256"),
                label=f"link receipt {role}",
            )
            try:
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise GateError("link_receipt", f"invalid JSON for {role}: {exc}") from exc
            if (
                not isinstance(receipt, dict)
                or receipt.get("schema") != LINK_SCHEMA
                or receipt.get("artifact_role") != role
                or receipt.get("artifact_sha256") != item["_sha256"]
                or receipt.get("generation_token") != token
                or receipt.get("output") != item.get("path")
            ):
                raise GateError("link_receipt", f"link receipt identity mismatch for {role}")
            argv = receipt.get("argv")
            inputs = receipt.get("inputs")
            if not isinstance(argv, list) or not all(isinstance(value, str) for value in argv):
                raise GateError("link_argv", f"argv is malformed for {role}")
            output_positions = [index for index, value in enumerate(argv) if value == "-o"]
            if len(output_positions) != 1 or output_positions[0] + 1 >= len(argv):
                raise GateError("link_output", f"{role} argv has no unique '-o OUTPUT'")
            output_arg = argv[output_positions[0] + 1]
            relative_output = item["path"]
            allowed_outputs = {
                relative_output,
                f"build/{relative_output}",
                str(self.build_root / relative_output),
            }
            if output_arg not in allowed_outputs:
                raise GateError(
                    "link_output",
                    f"{role} argv output does not name the receipt artifact: {output_arg}",
                )
            joined = " ".join(argv)
            zdefs = any(
                marker in joined
                for marker in ("-Wl,-z,defs", "-Wl,--no-undefined", "-Wl,-z,defs,")
            )
            no_allow = "--no-allow-shlib-undefined" in joined
            forbidden = [
                marker
                for marker in (
                    "--unresolved-symbols",
                    "ignore-all",
                    "ignore-in-object-files",
                    "-undefined dynamic_lookup",
                )
                if marker in joined
            ]
            if "--allow-shlib-undefined" in joined.replace("--no-allow-shlib-undefined", ""):
                forbidden.append("--allow-shlib-undefined")
            if not zdefs or not no_allow or forbidden:
                raise GateError(
                    "strict_link_argv",
                    f"{role} has no exact strict-link argv or contains {forbidden}",
                )
            if any(".." in path.parts for path in path_values_from_argv(argv)):
                raise GateError("argv_path_escape", f"{role} argv contains relative traversal")
            for absolute in absolute_paths_from_argv(argv):
                resolved = absolute.resolve(strict=False)
                if not (
                    is_relative_to(resolved, self.source_root)
                    or is_relative_to(resolved, self.build_root)
                ):
                    raise GateError("argv_path_escape", f"{role} argv escapes project: {absolute}")
            if not isinstance(inputs, list) or not inputs:
                raise GateError("link_inputs", f"{role} has no exact input list")
            for index, source in enumerate(inputs):
                if not isinstance(source, dict) or source.get("root") not in ("source", "build"):
                    raise GateError("link_inputs", f"{role} input {index} has an invalid root")
                root = self.source_root if source["root"] == "source" else self.build_root
                path = require_regular_under(
                    root, source.get("path"), field=f"{role} link input {index}"
                )
                self.observe(path, source.get("sha256"), label=f"{role} link input {index}")
        self.pass_gate("G14_STRICT_LINK_ARGV", "every generated artifact has byte-pinned strict linker argv")
        self.pass_gate("G15_PROJECT_LOCAL_INPUTS", "all argv and receipt inputs remain project-local and non-symlinked")

    def validate_symbols(self) -> None:
        for role, info in self.elf.items():
            visible = set(self.visible_namespaces(self.artifacts[role]["namespace"]))
            providers_by_symbol: dict[str, list[str]] = {}
            for provider_role, provider_info in self.elf.items():
                if self.artifacts[provider_role]["namespace"] not in visible:
                    continue
                for symbol in provider_info.strong_defined:
                    providers_by_symbol.setdefault(symbol, []).append(provider_role)
            for symbol in sorted(info.strong_undefined):
                providers = sorted(providers_by_symbol.get(symbol, []))
                if not providers:
                    raise GateError(
                        "strong_undefined",
                        f"{role} has unresolved strong UND {symbol}",
                    )
                if len(providers) != 1:
                    raise GateError(
                        "symbol_ambiguous",
                        f"{role} sees multiple strong providers for {symbol}: {providers}",
                    )
        self.pass_gate("G16_STRONG_UNDEFINED", "every strong UND has one reachable strong provider")

    def validate_generation_tokens(self) -> None:
        expected = self.manifest["generation_token"]
        generated = 0
        for role, item in self.artifacts.items():
            tokens = self.elf[role].generation_tokens
            if item["provenance"] == "generated":
                generated += 1
                if tokens != (expected,):
                    raise GateError(
                        "generation_token_mismatch",
                        f"{role} embedded tokens={tokens}, expected exactly {expected!r}",
                    )
            elif tokens:
                raise GateError(
                    "generation_token_scope",
                    f"immutable base {role} unexpectedly claims current generation token",
                )
        if generated < 3:
            raise GateError("generation_token_scope", "fewer than three generated artifacts are bound")
        self.pass_gate("G17_COMMON_GENERATION_TOKEN", f"{generated} generated ELF files embed one exact token")

    def validate_fd_admissions(self) -> None:
        values = self.manifest.get("fd_admissions")
        if not isinstance(values, list):
            raise GateError("fd_admission", "fd_admissions must be a list")
        by_role: dict[str, dict[str, Any]] = {}
        for item in values:
            if not isinstance(item, dict) or item.get("artifact_role") not in self.artifacts:
                raise GateError("fd_admission", "fd admission is malformed")
            role = item["artifact_role"]
            if role in by_role:
                raise GateError("fd_duplicate_mapping", f"duplicate fd admission for {role}")
            by_role[role] = item
        dynamic_roles = {item["artifact_role"] for item in self.manifest["dynamic_roots"]}
        if set(by_role) != dynamic_roles:
            raise GateError(
                "fd_admission",
                f"fd admissions must exactly cover dynamic roots: expected={sorted(dynamic_roles)} actual={sorted(by_role)}",
            )
        for role, item in by_role.items():
            if (
                item.get("mode") != "sealed_fd"
                or item.get("mapping_policy") != "single_identity"
                or set(item.get("open_flags", [])) != {"O_CLOEXEC", "O_NOFOLLOW"}
                or item.get("path") != self.artifacts[role]["path"]
            ):
                raise GateError("fd_admission", f"unsafe fd admission policy for {role}")
            actual = canonical_stat(self.artifacts[role]["_path"])
            for phase in ("path_before", "fd_before", "fd_after", "path_after"):
                if item.get(phase) != actual:
                    raise GateError("fd_path_swap", f"{role} {phase} differs from exact artifact identity")
            mappings = item.get("mappings")
            if not isinstance(mappings, list) or len(mappings) != 1:
                raise GateError("fd_duplicate_mapping", f"{role} has {len(mappings) if isinstance(mappings, list) else '?'} mappings")
            mapping = mappings[0]
            expected_mapping = dict(actual)
            expected_mapping["namespace"] = self.artifacts[role]["namespace"]
            if mapping != expected_mapping:
                raise GateError("fd_duplicate_mapping", f"{role} mapping identity/namespace is wrong")
        self.pass_gate("G18_FD_PATH_STABILITY", "path and fd identity agree before and after load")
        self.pass_gate("G19_SINGLE_MAPPING", "each dynamic root has one exact namespace mapping")

    def recheck_observed(self) -> None:
        for path, before in sorted(self.observed.items(), key=lambda item: str(item[0])):
            if not path.is_file() or path.is_symlink():
                raise GateError("input_changed", f"observed input disappeared/became symlink: {path}")
            after = sha256(path)
            if after != before:
                raise GateError("input_changed", f"observed input changed: {path}")
        self.pass_gate("G20_TOCTOU_REHASH", f"{len(self.observed)} inputs are unchanged after verification")

    def verify(self) -> dict[str, Any]:
        self.validate_roots()
        self.load_manifest()
        self.validate_source_snapshot()
        self.validate_namespaces_shape()
        self.validate_artifacts()
        self.validate_dynamic_roots()
        self.validate_source_contracts()
        self.validate_namespace_closure()
        self.validate_link_receipts()
        self.validate_symbols()
        self.validate_generation_tokens()
        self.validate_fd_admissions()
        self.recheck_observed()
        observation = tree_digest((str(path), digest) for path, digest in self.observed.items())
        return {
            "schema": REPORT_SCHEMA,
            "eligible_for_route_a_device_admission": True,
            "evidence_level": "host_artifact_verified",
            "device_verified": False,
            "first_frame_proven": False,
            "generation_id": self.manifest["generation_id"],
            "generation_token": self.manifest["generation_token"],
            "manifest_sha256": self.observed[self.manifest_path],
            "observation_id": observation,
            "decision_scope": "exact source/artifact/receipt bytes only",
            "checks": self.checks,
            "errors": [],
        }


def choose_readelf(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("READELF")
    if env:
        return Path(env)
    candidates = [
        shutil.which("llvm-readelf"),
        shutil.which("readelf"),
        "/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin/llvm-readelf",
    ]
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value)
    raise GateError("tool_missing", "pass --readelf or set READELF")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--build-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--readelf")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)

    if args.report is not None and not is_relative_to(
        args.report.resolve(strict=False), args.build_root.resolve()
    ):
        parser.error("--report must remain under --build-root")

    checks: list[dict[str, str]] = []
    try:
        verifier = Verifier(
            project_root=args.project_root,
            source_root=args.source_root,
            build_root=args.build_root,
            manifest_path=args.manifest,
            readelf=choose_readelf(args.readelf),
        )
        payload = verifier.verify()
        rc = 0
    except GateError as exc:
        if "verifier" in locals():
            checks = verifier.checks
        payload = {
            "schema": REPORT_SCHEMA,
            "eligible_for_route_a_device_admission": False,
            "evidence_level": "host_rejected",
            "device_verified": False,
            "first_frame_proven": False,
            "decision_scope": "exact source/artifact/receipt bytes only",
            "checks": checks,
            "errors": [{"code": exc.code, "detail": exc.detail}],
        }
        rc = 1
    payload["observed_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    if args.report:
        atomic_write_json(args.report, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
