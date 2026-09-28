#!/usr/bin/env python3
"""Fail-closed certificate for the appspawn-x pre-prepare ELF universe.

The gate is intentionally static and conservative.  It binds an immutable,
project-local snapshot to an exact main ELF and exact observed musl loader,
resolves the recursive DT_NEEDED graph through a sealed directory order, and
scans every resolved executable segment for TPIDR_EL0-derived memory accesses.

It does *not* infer execution order from module membership or source comments.
PRE_PREPARE and POST_PREPARE classifications require a separate binary
callgraph/phase proof bound to the same main SHA.  Without that proof,
slot-5 accesses remain UNORDERED_RELATIVE_TO_PREPARE and the gate fails closed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import struct
import sys
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable, Optional


SCHEMA_CONFIG = "westlake-initial-closure-gate-config-v1"
SCHEMA_MANIFEST = "westlake-immutable-snapshot-manifest-v1"
SCHEMA_CERTIFICATE = "westlake-initial-closure-certificate-v1"
SCHEMA_PHASE = "westlake-tls-prepare-order-evidence-v1"

EM_AARCH64 = 183
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
PT_NOTE = 4
PT_TLS = 7
PF_X = 1
PF_W = 2

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
DT_RPATH = 15
DT_TEXTREL = 22
DT_RUNPATH = 29
DT_FLAGS = 30
DF_TEXTREL = 4

SHT_SYMTAB = 2
SHT_DYNSYM = 11
SHN_UNDEF = 0

MUSL_RESERVED = {
    "libc.so",
    "libpthread.so",
    "librt.so",
    "libm.so",
    "libdl.so",
    "libutil.so",
    "libxnet.so",
}


class GateFailure(RuntimeError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_atomic(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".new")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def find_project_root(start: pathlib.Path) -> pathlib.Path:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "adapter").is_dir() and candidate.name == "02.unity.cardwords":
            return candidate
    raise GateFailure(
        "PROJECT_ROOT_NOT_FOUND",
        "gate must execute from the CardWords project-local tool copy",
        start=str(start),
    )


PROJECT_ROOT = find_project_root(pathlib.Path(__file__).parent)


def project_path(
    raw: str | pathlib.Path,
    *,
    role: str,
    file: bool = False,
    directory: bool = False,
    must_exist: bool = True,
) -> pathlib.Path:
    path = pathlib.Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if path.is_symlink():
        raise GateFailure(
            "SYMLINK_INPUT_FORBIDDEN", "certificate inputs may not be symlinks", role=role, path=str(path)
        )
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError as exc:
        raise GateFailure(
            "PROJECT_INPUT_MISSING", "project-local input cannot be resolved", role=role, path=str(path), error=str(exc)
        ) from exc
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise GateFailure(
            "INPUT_OUTSIDE_PROJECT",
            "every certificate input and output must remain inside the current project",
            role=role,
            path=str(path),
            resolved=str(resolved),
        ) from exc
    if must_exist and file and not resolved.is_file():
        raise GateFailure("INPUT_NOT_FILE", "expected a regular file", role=role, path=str(resolved))
    if must_exist and directory and not resolved.is_dir():
        raise GateFailure("INPUT_NOT_DIRECTORY", "expected a directory", role=role, path=str(resolved))
    return resolved


@dataclass(frozen=True)
class ProgramHeader:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int


@dataclass(frozen=True)
class SectionHeader:
    sh_name: int
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int


class Elf64:
    """Strict target-independent reader for the ELF facts used by this gate."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path.resolve()
        if path.is_symlink():
            raise GateFailure("SYMLINK_ELF_FORBIDDEN", "ELF input may not be a symlink", path=str(path))
        try:
            fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise GateFailure("ELF_NOT_REGULAR", "ELF input is not regular", path=str(path))
                chunks: list[bytes] = []
                while True:
                    chunk = os.read(fd, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                after = os.fstat(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            raise GateFailure("ELF_READ_FAILED", str(exc), path=str(path)) from exc
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        if identity_before != identity_after:
            raise GateFailure(
                "ELF_CHANGED_DURING_READ", "ELF metadata changed while read", path=str(path), before=identity_before,
                after=identity_after,
            )
        self.data = b"".join(chunks)
        if len(self.data) != before.st_size:
            raise GateFailure("ELF_SHORT_READ", "ELF byte count differs from stat", path=str(path))
        self.sha256 = sha256_bytes(self.data)
        self.file_identity = (before.st_dev, before.st_ino)
        if len(self.data) < 64 or self.data[:4] != b"\x7fELF":
            raise GateFailure("NOT_ELF", "input is not ELF", path=str(path))
        if self.data[4:7] != bytes((2, 1, 1)):
            raise GateFailure("ELF_FORMAT", "only ELF64 little-endian v1 is accepted", path=str(path))
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        (
            _, self.e_type, self.e_machine, self.e_version, self.e_entry, self.e_phoff, self.e_shoff,
            self.e_flags, self.e_ehsize, self.e_phentsize, self.e_phnum, self.e_shentsize, self.e_shnum,
            self.e_shstrndx,
        ) = header
        if self.e_machine != EM_AARCH64:
            raise GateFailure("ELF_MACHINE", "only AArch64 target ELFs are accepted", path=str(path), machine=self.e_machine)
        self.program_headers = self._program_headers()
        self.section_headers = self._section_headers()
        self.dynamic = self._dynamic_entries()
        self.needed = [self._dynamic_string(value) for tag, value in self.dynamic if tag == DT_NEEDED]
        self.soname = self._last_dynamic_string(DT_SONAME)
        self.rpaths = [self._dynamic_string(value) for tag, value in self.dynamic if tag == DT_RPATH]
        self.runpaths = [self._dynamic_string(value) for tag, value in self.dynamic if tag == DT_RUNPATH]
        self.has_textrel = any(
            tag == DT_TEXTREL or (tag == DT_FLAGS and bool(value & DF_TEXTREL)) for tag, value in self.dynamic
        )
        self.build_id = self._build_id()
        self.tls = self._single_program_header(PT_TLS)
        self.defined_symbols = self._defined_symbols()

    def _range(self, offset: int, size: int, role: str) -> None:
        if offset < 0 or size < 0 or offset > len(self.data) or size > len(self.data) - offset:
            raise GateFailure(
                "ELF_RANGE", "ELF structure lies outside file", path=str(self.path), role=role, offset=offset,
                size=size, file_size=len(self.data),
            )

    def _program_headers(self) -> list[ProgramHeader]:
        if self.e_phnum and self.e_phentsize < 56:
            raise GateFailure("ELF_PHENTSIZE", "program header entry is truncated", path=str(self.path))
        self._range(self.e_phoff, self.e_phnum * self.e_phentsize, "program_headers")
        result: list[ProgramHeader] = []
        for index in range(self.e_phnum):
            result.append(ProgramHeader(*struct.unpack_from("<IIQQQQQQ", self.data, self.e_phoff + index * self.e_phentsize)))
        return result

    def _section_headers(self) -> list[SectionHeader]:
        if not self.e_shnum:
            return []
        if self.e_shentsize < 64:
            raise GateFailure("ELF_SHENTSIZE", "section header entry is truncated", path=str(self.path))
        self._range(self.e_shoff, self.e_shnum * self.e_shentsize, "section_headers")
        result: list[SectionHeader] = []
        for index in range(self.e_shnum):
            result.append(SectionHeader(*struct.unpack_from("<IIQQQQIIQQ", self.data, self.e_shoff + index * self.e_shentsize)))
        return result

    def _single_program_header(self, kind: int) -> Optional[ProgramHeader]:
        entries = [header for header in self.program_headers if header.p_type == kind]
        if len(entries) > 1:
            raise GateFailure("ELF_MULTIPLE_SEGMENT", "ELF has multiple singleton segments", path=str(self.path), kind=kind)
        return entries[0] if entries else None

    def _dynamic_entries(self) -> list[tuple[int, int]]:
        segment = self._single_program_header(PT_DYNAMIC)
        if segment is None:
            return []
        if segment.p_filesz % 16:
            raise GateFailure("DYNAMIC_SIZE", "PT_DYNAMIC is not an Elf64_Dyn multiple", path=str(self.path))
        self._range(segment.p_offset, segment.p_filesz, "PT_DYNAMIC")
        result: list[tuple[int, int]] = []
        for offset in range(segment.p_offset, segment.p_offset + segment.p_filesz, 16):
            tag, value = struct.unpack_from("<qQ", self.data, offset)
            result.append((tag, value))
            if tag == DT_NULL:
                return result
        raise GateFailure("DYNAMIC_NO_NULL", "PT_DYNAMIC has no DT_NULL", path=str(self.path))

    def _vaddr_to_offset(self, address: int, size: int) -> int:
        for header in self.program_headers:
            if header.p_type != PT_LOAD:
                continue
            if header.p_vaddr <= address and address - header.p_vaddr <= header.p_filesz - size:
                return header.p_offset + address - header.p_vaddr
        raise GateFailure("ELF_VADDR_UNMAPPED", "virtual address has no file bytes", path=str(self.path), address=address)

    def _dynamic_strtab(self) -> tuple[int, int]:
        addresses = [value for tag, value in self.dynamic if tag == DT_STRTAB]
        sizes = [value for tag, value in self.dynamic if tag == DT_STRSZ]
        if len(addresses) != 1 or len(sizes) != 1:
            raise GateFailure("DYNAMIC_STRTAB", "dynamic string table missing or ambiguous", path=str(self.path))
        return self._vaddr_to_offset(addresses[0], sizes[0]), sizes[0]

    def _dynamic_string(self, index: int) -> str:
        base, size = self._dynamic_strtab()
        if index >= size:
            raise GateFailure("DYNAMIC_STRING_INDEX", "dynamic string index outside table", path=str(self.path))
        end = self.data.find(b"\0", base + index, base + size)
        if end < 0:
            raise GateFailure("DYNAMIC_STRING_NUL", "dynamic string is not terminated", path=str(self.path))
        return self.data[base + index:end].decode("utf-8", errors="strict")

    def _last_dynamic_string(self, tag: int) -> Optional[str]:
        values = [value for found, value in self.dynamic if found == tag]
        return self._dynamic_string(values[-1]) if values else None

    def _build_id(self) -> Optional[str]:
        found: list[str] = []
        for header in self.program_headers:
            if header.p_type != PT_NOTE:
                continue
            self._range(header.p_offset, header.p_filesz, "PT_NOTE")
            offset = header.p_offset
            end = offset + header.p_filesz
            while offset + 12 <= end:
                namesz, descsz, note_type = struct.unpack_from("<III", self.data, offset)
                name_start = offset + 12
                name_end = name_start + namesz
                desc_start = (name_end + 3) & ~3
                desc_end = desc_start + descsz
                next_offset = (desc_end + 3) & ~3
                if desc_end > end or next_offset <= offset:
                    raise GateFailure("ELF_NOTE_RANGE", "malformed ELF note", path=str(self.path))
                name = self.data[name_start:name_end]
                if note_type == 3 and name.rstrip(b"\0") == b"GNU":
                    found.append(self.data[desc_start:desc_end].hex())
                offset = next_offset
        unique = sorted(set(found))
        if len(unique) > 1:
            raise GateFailure("BUILD_ID_AMBIGUOUS", "ELF has multiple Build-IDs", path=str(self.path), build_ids=unique)
        return unique[0] if unique else None

    def _defined_symbols(self) -> set[str]:
        result: set[str] = set()
        for section in self.section_headers:
            if section.sh_type not in (SHT_SYMTAB, SHT_DYNSYM):
                continue
            if section.sh_link >= len(self.section_headers):
                raise GateFailure("SYMTAB_LINK", "symbol table has invalid string table link", path=str(self.path))
            strings = self.section_headers[section.sh_link]
            self._range(strings.sh_offset, strings.sh_size, "symbol_strings")
            entry_size = section.sh_entsize or 24
            if entry_size < 24 or section.sh_size % entry_size:
                raise GateFailure("SYMTAB_SIZE", "symbol table has invalid entry size", path=str(self.path))
            self._range(section.sh_offset, section.sh_size, "symbols")
            for offset in range(section.sh_offset, section.sh_offset + section.sh_size, entry_size):
                name_index, _info, _other, shndx, _value, _size = struct.unpack_from("<IBBHQQ", self.data, offset)
                if shndx == SHN_UNDEF or name_index >= strings.sh_size:
                    continue
                start = strings.sh_offset + name_index
                end = self.data.find(b"\0", start, strings.sh_offset + strings.sh_size)
                if end < 0:
                    raise GateFailure("SYMBOL_STRING_NUL", "symbol name is not terminated", path=str(self.path))
                if end > start:
                    result.add(self.data[start:end].decode("utf-8", errors="replace"))
        return result

    def executable_segments(self) -> Iterable[tuple[int, bytes]]:
        for header in self.program_headers:
            if header.p_type != PT_LOAD or not (header.p_flags & PF_X) or not header.p_filesz:
                continue
            self._range(header.p_offset, header.p_filesz, "executable_PT_LOAD")
            yield header.p_vaddr, self.data[header.p_offset:header.p_offset + header.p_filesz]

    def identity_dict(self, relative_to: pathlib.Path) -> dict[str, Any]:
        tls = None
        if self.tls is not None:
            tls = {
                "filesz": self.tls.p_filesz,
                "memsz": self.tls.p_memsz,
                "align": max(self.tls.p_align, 1),
                "vaddr": self.tls.p_vaddr,
            }
        return {
            "path": str(self.path.relative_to(relative_to)),
            "sha256": self.sha256,
            "build_id": self.build_id,
            "elf_type": self.e_type,
            "soname": self.soname,
            "needed": self.needed,
            "pt_tls": tls,
            "rpath": self.rpaths,
            "runpath": self.runpaths,
            "textrel": self.has_textrel,
        }

    def load_fingerprint(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for header in self.program_headers:
            if header.p_type != PT_LOAD or not (header.p_flags & (PF_X | PF_W)):
                continue
            self._range(header.p_offset, header.p_filesz, "PT_LOAD_fingerprint")
            result.append({
                "offset": header.p_offset,
                "vaddr": header.p_vaddr,
                "filesz": header.p_filesz,
                "memsz": header.p_memsz,
                "flags": header.p_flags,
                "align": max(header.p_align, 1),
                "bytes_sha256": sha256_bytes(self.data[header.p_offset:header.p_offset + header.p_filesz]),
            })
        return result


def make_snapshot_manifest(snapshot_root: pathlib.Path) -> dict[str, Any]:
    snapshot_root = project_path(snapshot_root, role="snapshot_root", directory=True)
    entries: list[dict[str, Any]] = []
    for path in sorted(snapshot_root.rglob("*")):
        if path.is_symlink():
            raise GateFailure("SNAPSHOT_SYMLINK", "immutable snapshot may not contain symlinks", path=str(path))
        if path.is_dir():
            continue
        if not path.is_file():
            raise GateFailure("SNAPSHOT_NONREGULAR", "immutable snapshot contains non-regular entry", path=str(path))
        info = path.stat()
        entries.append({
            "path": str(path.relative_to(snapshot_root)),
            "sha256": sha256_file(path),
            "size": info.st_size,
            "mode": stat.S_IMODE(info.st_mode),
        })
    return {
        "schema": SCHEMA_MANIFEST,
        "snapshot_root": str(snapshot_root.relative_to(PROJECT_ROOT)),
        "entry_count": len(entries),
        "entries": entries,
    }


def validate_snapshot_manifest(
    snapshot_root: pathlib.Path, manifest_path: pathlib.Path, expected_manifest_sha: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    actual_manifest_sha = sha256_file(manifest_path)
    if actual_manifest_sha != expected_manifest_sha:
        errors.append(GateFailure(
            "SNAPSHOT_MANIFEST_IDENTITY",
            "snapshot manifest SHA differs from config binding",
            expected=expected_manifest_sha,
            actual=actual_manifest_sha,
        ).as_dict())
    try:
        expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(GateFailure("SNAPSHOT_MANIFEST_READ", str(exc), path=str(manifest_path)).as_dict())
        return {"manifest_sha256": actual_manifest_sha, "valid": False}, errors
    if expected.get("schema") != SCHEMA_MANIFEST:
        errors.append(GateFailure("SNAPSHOT_MANIFEST_SCHEMA", "unsupported manifest schema").as_dict())
    try:
        actual = make_snapshot_manifest(snapshot_root)
    except GateFailure as exc:
        errors.append(exc.as_dict())
        return {"manifest_sha256": actual_manifest_sha, "valid": False}, errors
    expected_core = dict(expected)
    expected_core["snapshot_root"] = str(snapshot_root.relative_to(PROJECT_ROOT))
    if actual != expected_core:
        expected_map = {item.get("path"): item for item in expected.get("entries", []) if isinstance(item, dict)}
        actual_map = {item["path"]: item for item in actual["entries"]}
        errors.append(GateFailure(
            "SNAPSHOT_CONTENT_MISMATCH",
            "snapshot membership, hash, size, or mode differs from immutable manifest",
            missing=sorted(set(expected_map) - set(actual_map)),
            added=sorted(set(actual_map) - set(expected_map)),
            changed=sorted(path for path in set(expected_map) & set(actual_map) if expected_map[path] != actual_map[path]),
        ).as_dict())
    return {
        "manifest_path": str(manifest_path.relative_to(PROJECT_ROOT)),
        "manifest_sha256": actual_manifest_sha,
        "entry_count": actual.get("entry_count"),
        "valid": not errors,
    }, errors


@dataclass
class ClosureObject:
    elf: Elf64
    load_name: str
    needed_by: Optional[str]
    category: str


class Resolver:
    def __init__(self, snapshot_root: pathlib.Path, loader: Elf64, search_dirs: list[pathlib.Path]) -> None:
        self.snapshot_root = snapshot_root
        self.loader = loader
        self.search_dirs = search_dirs
        self.audits: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def _relative(self, path: pathlib.Path) -> str:
        return str(path.relative_to(self.snapshot_root))

    def _candidates(self, name: str, needed_by: Elf64) -> list[pathlib.Path]:
        candidates: list[pathlib.Path] = []
        for directory in self.search_dirs:
            candidate = directory / name
            if candidate.is_symlink():
                self.errors.append(GateFailure(
                    "PROVIDER_SYMLINK", "provider candidate may not be a symlink", needed=name, path=str(candidate)
                ).as_dict())
                continue
            if candidate.is_file():
                candidates.append(candidate.resolve())
        self.audits.append({
            "needed": name,
            "needed_by": self._relative(needed_by.path),
            "search_order": [self._relative(directory) for directory in self.search_dirs],
            "candidates": [self._relative(path) for path in candidates],
            "candidate_count": len(candidates),
        })
        return candidates

    def resolve(self, roots: list[tuple[Elf64, str]]) -> list[ClosureObject]:
        objects: list[ClosureObject] = []
        queue: deque[ClosureObject] = deque()
        by_path: dict[pathlib.Path, ClosureObject] = {}
        by_shortname: dict[str, ClosureObject] = {}
        loader_object: Optional[ClosureObject] = None
        for elf, category in roots:
            obj = ClosureObject(elf, "$MAIN" if category == "initial_main" else elf.path.name, None, category)
            objects.append(obj)
            queue.append(obj)
            by_path[elf.path] = obj

        while queue:
            current = queue.popleft()
            if current.category == "musl_loader":
                continue
            for needed in current.elf.needed:
                if needed in MUSL_RESERVED:
                    if loader_object is None:
                        loader_object = ClosureObject(
                            self.loader, "$MUSL_LOADER", self._relative(current.elf.path), "musl_loader"
                        )
                        objects.append(loader_object)
                        by_path[self.loader.path] = loader_object
                        for alias in MUSL_RESERVED:
                            by_shortname[alias] = loader_object
                    self.audits.append({
                        "needed": needed,
                        "needed_by": self._relative(current.elf.path),
                        "resolution": "MUSL_RESERVED_TO_EXACT_LOADER",
                        "provider": self._relative(self.loader.path),
                        "provider_sha256": self.loader.sha256,
                    })
                    continue
                if "/" in needed:
                    self.errors.append(GateFailure(
                        "EXPLICIT_DT_NEEDED_UNSUPPORTED",
                        "certificate does not guess the cwd/root mapping for slash-bearing DT_NEEDED",
                        needed=needed,
                        needed_by=self._relative(current.elf.path),
                    ).as_dict())
                    continue
                candidates = self._candidates(needed, current.elf)
                if not candidates:
                    self.errors.append(GateFailure(
                        "NEEDED_NOT_FOUND",
                        "DT_NEEDED has no provider in the sealed candidate search order",
                        needed=needed,
                        needed_by=self._relative(current.elf.path),
                    ).as_dict())
                    continue
                if len(candidates) != 1:
                    self.errors.append(GateFailure(
                        "NEEDED_AMBIGUOUS",
                        "DT_NEEDED resolves to more than one path; byte equality does not make provider choice unique",
                        needed=needed,
                        needed_by=self._relative(current.elf.path),
                        candidates=[self._relative(path) for path in candidates],
                    ).as_dict())
                    continue
                path = candidates[0]
                prior = by_shortname.get(needed)
                if prior is not None:
                    if prior.elf.path != path:
                        self.errors.append(GateFailure(
                            "LOADED_SHORTNAME_MISMATCH",
                            "an already-loaded shortname differs from the sealed provider result",
                            needed=needed,
                            loaded=self._relative(prior.elf.path),
                            searched=self._relative(path),
                        ).as_dict())
                    continue
                if path in by_path:
                    by_shortname[needed] = by_path[path]
                    continue
                try:
                    elf = Elf64(path)
                except GateFailure as exc:
                    self.errors.append(exc.as_dict())
                    continue
                if elf.soname is not None and elf.soname != needed:
                    self.errors.append(GateFailure(
                        "PROVIDER_SONAME_MISMATCH",
                        "provider SONAME differs from consumer DT_NEEDED identity",
                        needed=needed,
                        provider=self._relative(path),
                        soname=elf.soname,
                    ).as_dict())
                obj = ClosureObject(elf, needed, self._relative(current.elf.path), current.category)
                objects.append(obj)
                queue.append(obj)
                by_path[path] = obj
                by_shortname[needed] = obj
                if elf.soname:
                    claimed = by_shortname.get(elf.soname)
                    if claimed is not None and claimed.elf.path != path:
                        self.errors.append(GateFailure(
                            "SONAME_COLLISION", "two paths claim one load-visible SONAME", soname=elf.soname,
                            first=self._relative(claimed.elf.path), second=self._relative(path),
                        ).as_dict())
                    else:
                        by_shortname[elf.soname] = obj
        return objects


def sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


def is_tpidr_el0_mrs(word: int) -> bool:
    return (word & 0xFFFFFFE0) == 0xD53BD040


def decode_unsigned_memory(word: int) -> Optional[dict[str, Any]]:
    # A64 Load/store register (unsigned immediate), including byte/half/word/xword.
    if (word & 0x3B000000) != 0x39000000:
        return None
    size = (word >> 30) & 0x3
    opc = (word >> 22) & 0x3
    if opc not in (0, 1, 2, 3):
        return None
    width = 1 << size
    direction = "write" if opc == 0 else "read"
    return {
        "base": (word >> 5) & 0x1F,
        "rt": word & 0x1F,
        "offset": ((word >> 10) & 0xFFF) * width,
        "width": width,
        "direction": direction,
    }


def decode_add_sub_immediate(word: int) -> Optional[dict[str, Any]]:
    if (word & 0x1F000000) != 0x11000000 or not (word & (1 << 31)):
        return None
    immediate = (word >> 10) & 0xFFF
    if word & (1 << 22):
        immediate <<= 12
    if word & (1 << 30):
        immediate = -immediate
    return {"dst": word & 0x1F, "src": (word >> 5) & 0x1F, "delta": immediate}


def decode_mov_register(word: int) -> Optional[dict[str, int]]:
    # MOV Xd, Xm alias of ORR Xd, XZR, Xm with no shift.
    if (word & 0xFFE0FFE0) != 0xAA0003E0:
        return None
    return {"dst": word & 0x1F, "src": (word >> 16) & 0x1F}


def is_control_flow(word: int) -> bool:
    return (
        (word & 0x7C000000) == 0x14000000  # B/BL immediate
        or (word & 0xFF000010) == 0x54000000  # B.cond
        or (word & 0x7E000000) == 0x34000000  # CBZ/CBNZ
        or (word & 0x7E000000) == 0x36000000  # TBZ/TBNZ
        or (word & 0xFFFFFC1F) in (0xD61F0000, 0xD63F0000, 0xD65F0000)  # BR/BLR/RET
    )


def is_return(word: int) -> bool:
    return (word & 0xFFFFFC1F) == 0xD65F0000


def scan_code_bytes(code: bytes, base_address: int, slot_offset: int, slot_width: int, window: int) -> dict[str, Any]:
    """Conservative local data flow over raw AArch64 words.

    Every unmodelled use while a TP-derived value is live becomes an explicit
    unknown.  The small decoder is therefore allowed to be incomplete but is
    not allowed to silently turn incomplete decoding into a zero count.
    """
    words: list[tuple[int, int]] = []
    first = (-base_address) & 3
    for offset in range(first, len(code) - 3, 4):
        words.append((base_address + offset, struct.unpack_from("<I", code, offset)[0]))
    sites: list[dict[str, Any]] = []
    for index, (address, word) in enumerate(words):
        if not is_tpidr_el0_mrs(word):
            continue
        destination = word & 0x1F
        origins: dict[int, int] = {destination: 0}
        accesses: list[dict[str, Any]] = []
        unknown: Optional[dict[str, Any]] = None
        terminated = False
        for step, (current_address, current) in enumerate(words[index + 1:index + 1 + window], start=1):
            memory = decode_unsigned_memory(current)
            if memory is not None:
                base = memory["base"]
                rt = memory["rt"]
                if base in origins:
                    tp_offset = origins[base] + memory["offset"]
                    access = {
                        "address": current_address,
                        "offset": tp_offset,
                        "width": memory["width"],
                        "direction": memory["direction"],
                        "encoding": f"0x{current:08x}",
                        "overlaps_slot5": max(tp_offset, slot_offset) < min(
                            tp_offset + memory["width"], slot_offset + slot_width
                        ),
                    }
                    accesses.append(access)
                if memory["direction"] == "read":
                    origins.pop(rt, None)
                elif rt in origins and base not in origins:
                    unknown = {
                        "address": current_address,
                        "reason": "TP_VALUE_ESCAPES_THROUGH_STORE",
                        "encoding": f"0x{current:08x}",
                    }
                    break
                if not origins:
                    terminated = True
                    break
                continue
            arithmetic = decode_add_sub_immediate(current)
            if arithmetic is not None:
                dst, src = arithmetic["dst"], arithmetic["src"]
                if src in origins and dst != 31:
                    origins[dst] = origins[src] + arithmetic["delta"]
                else:
                    origins.pop(dst, None)
                if not origins:
                    terminated = True
                    break
                continue
            move = decode_mov_register(current)
            if move is not None:
                if move["src"] in origins and move["dst"] != 31:
                    origins[move["dst"]] = origins[move["src"]]
                else:
                    origins.pop(move["dst"], None)
                if not origins:
                    terminated = True
                    break
                continue
            if current == 0xD503201F:  # NOP
                continue
            if is_return(current):
                # Caller-saved non-return registers die at RET.  x0 returning
                # TP, or a callee-saved TP value, escapes this local proof.
                escaping = sorted(reg for reg in origins if reg == 0 or 19 <= reg <= 28)
                if escaping:
                    unknown = {
                        "address": current_address,
                        "reason": "TP_VALUE_ESCAPES_FUNCTION",
                        "registers": escaping,
                        "encoding": f"0x{current:08x}",
                    }
                terminated = True
                break
            if is_control_flow(current):
                unknown = {
                    "address": current_address,
                    "reason": "CONTROL_FLOW_REQUIRES_INTERPROCEDURAL_CFG",
                    "encoding": f"0x{current:08x}",
                }
                break
            unknown = {
                "address": current_address,
                "reason": "UNMODELLED_INSTRUCTION_WITH_LIVE_TP_PROVENANCE",
                "encoding": f"0x{current:08x}",
            }
            break
        else:
            if origins:
                unknown = {
                    "address": address,
                    "reason": "LOCAL_WINDOW_EXHAUSTED_WITH_LIVE_TP_PROVENANCE",
                    "window": window,
                }
            else:
                terminated = True
        sites.append({
            "mrs_address": address,
            "destination_register": destination,
            "encoding": f"0x{word:08x}",
            "accesses": accesses,
            "unknown": unknown,
            "local_flow_terminated": terminated and unknown is None,
        })
    all_accesses = [access for site in sites for access in site["accesses"]]
    unknowns = [site["unknown"] | {"mrs_address": site["mrs_address"]} for site in sites if site["unknown"]]
    return {
        "mrs_count": len(sites),
        "access_count": len(all_accesses),
        "slot5_access_count": sum(1 for access in all_accesses if access["overlaps_slot5"]),
        "unknown_count": len(unknowns),
        "sites": sites,
        "unknowns": unknowns,
    }


def scan_elf(elf: Elf64, snapshot_root: pathlib.Path, slot_offset: int, slot_width: int, window: int) -> dict[str, Any]:
    segment_reports: list[dict[str, Any]] = []
    for base, code in elf.executable_segments():
        report = scan_code_bytes(code, base, slot_offset, slot_width, window)
        report["base_address"] = base
        report["byte_size"] = len(code)
        segment_reports.append(report)
    sites = [site for segment in segment_reports for site in segment["sites"]]
    unknowns = [item for segment in segment_reports for item in segment["unknowns"]]
    accesses = [access | {"mrs_address": site["mrs_address"]} for site in sites for access in site["accesses"]]
    return {
        "path": str(elf.path.relative_to(snapshot_root)),
        "sha256": elf.sha256,
        "build_id": elf.build_id,
        "mrs_count": len(sites),
        "access_count": len(accesses),
        "slot5_access_count": sum(1 for access in accesses if access["overlaps_slot5"]),
        "unknown_count": len(unknowns),
        "accesses": accesses,
        "unknowns": unknowns,
        "segments": segment_reports,
    }


def parse_search_order_evidence(config: dict[str, Any], snapshot_root: pathlib.Path) -> dict[str, Any]:
    evidence = config.get("production_search_order_evidence")
    result: dict[str, Any] = {
        "proven": False,
        "method": None,
        "expected_target_order": [item.get("target") for item in config.get("sealed_candidate_search_order", [])],
    }
    if not isinstance(evidence, dict):
        result["reason"] = "NO_EVIDENCE_OBJECT"
        return result
    result["method"] = evidence.get("method")
    if evidence.get("method") != "appspawn_init_ld_library_path_exact":
        result["reason"] = "UNSUPPORTED_OR_NONEXACT_METHOD"
        return result
    raw_path = evidence.get("artifact")
    if not isinstance(raw_path, str):
        result["reason"] = "EVIDENCE_ARTIFACT_MISSING"
        return result
    path = (snapshot_root / raw_path).resolve()
    try:
        path.relative_to(snapshot_root)
    except ValueError:
        result["reason"] = "EVIDENCE_ESCAPES_SNAPSHOT"
        return result
    if not path.is_file() or path.is_symlink():
        result["reason"] = "EVIDENCE_NOT_REGULAR"
        return result
    result["artifact"] = str(path.relative_to(snapshot_root))
    result["artifact_sha256"] = sha256_file(path)
    try:
        init_config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result["reason"] = "EVIDENCE_PARSE_FAILED"
        result["error"] = str(exc)
        return result
    service_name = evidence.get("service", "appspawn-x")
    services = init_config.get("services")
    service = next(
        (item for item in services if isinstance(item, dict) and item.get("name") == service_name), None
    ) if isinstance(services, list) else None
    if service is None:
        result["reason"] = "SERVICE_NOT_FOUND"
        return result
    values = []
    for item in service.get("env", []):
        if isinstance(item, dict) and item.get("name") == "LD_LIBRARY_PATH":
            values.append(item.get("value"))
    if len(values) != 1 or not isinstance(values[0], str):
        result["reason"] = "LD_LIBRARY_PATH_MISSING_OR_AMBIGUOUS"
        return result
    actual_order = values[0].split(":")
    expected_order = result["expected_target_order"]
    result["observed_target_order"] = actual_order
    result["proven"] = actual_order == expected_order
    result["reason"] = "EXACT_MATCH" if result["proven"] else "ARCH_OR_ORDER_MISMATCH"
    return result


def sidecar_audit(main: Elf64, sidecar: Elf64, snapshot_root: pathlib.Path) -> dict[str, Any]:
    main_tls = None if main.tls is None else (
        main.tls.p_offset, main.tls.p_vaddr, main.tls.p_filesz, main.tls.p_memsz, max(main.tls.p_align, 1)
    )
    sidecar_tls = None if sidecar.tls is None else (
        sidecar.tls.p_offset, sidecar.tls.p_vaddr, sidecar.tls.p_filesz, sidecar.tls.p_memsz,
        max(sidecar.tls.p_align, 1),
    )
    checks = {
        "same_nonempty_build_id": bool(main.build_id and main.build_id == sidecar.build_id),
        "same_type_and_entry": main.e_type == sidecar.e_type and main.e_entry == sidecar.e_entry,
        "same_needed_and_soname": main.needed == sidecar.needed and main.soname == sidecar.soname,
        "same_pt_tls": main_tls == sidecar_tls,
        "same_executable_writable_loads": main.load_fingerprint() == sidecar.load_fingerprint(),
    }
    return {
        "main": main.identity_dict(snapshot_root),
        "sidecar": sidecar.identity_dict(snapshot_root),
        "checks": checks,
        "valid": all(checks.values()),
    }


def evaluate_phase(
    config: dict[str, Any], main: Elf64, main_sidecar: Elf64, scan_objects: list[dict[str, Any]],
    snapshot_root: pathlib.Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    phase_config = config.get("phase_evidence")
    expected_symbols = config.get("expected_prepare_symbols", [])
    symbols = sorted(
        symbol for symbol in expected_symbols
        if isinstance(symbol, str) and symbol in main_sidecar.defined_symbols
    )
    observed_slot5 = sum(item["slot5_access_count"] for item in scan_objects)
    phase: dict[str, Any] = {
        "expected_prepare_symbols": expected_symbols,
        "defined_prepare_symbols": symbols,
        "prepare_point_status": "PRESENT_UNORDERED" if symbols else "ABSENT",
        "prepare_order_proven": False,
        "pre_prepare": {"slot5_access_count": None, "classification": "NOT_PROVEN"},
        "post_prepare": {"slot5_access_count": None, "classification": "NOT_PROVEN"},
        "unordered_relative_to_prepare": {"observed_slot5_access_count": observed_slot5},
        "evidence": None,
    }
    if not symbols:
        errors.append(GateFailure(
            "TLS_PREPARE_SYMBOL_ABSENT",
            "the exact final main sidecar defines no admitted native-compat prepare entry point",
            expected_symbols=expected_symbols,
        ).as_dict())
    if not isinstance(phase_config, dict) or not isinstance(phase_config.get("artifact"), str):
        errors.append(GateFailure(
            "TLS_PREPARE_ORDER_NOT_PROVEN",
            "no binary callgraph/phase evidence artifact binds prepare before every slot-5 consumer",
        ).as_dict())
        return phase, errors
    evidence_path = (snapshot_root / phase_config["artifact"]).resolve()
    try:
        evidence_path.relative_to(snapshot_root)
    except ValueError:
        errors.append(GateFailure("PHASE_EVIDENCE_ESCAPES_SNAPSHOT", "phase evidence escapes snapshot").as_dict())
        return phase, errors
    if not evidence_path.is_file() or evidence_path.is_symlink():
        errors.append(GateFailure("PHASE_EVIDENCE_MISSING", "phase evidence is not a regular frozen file").as_dict())
        return phase, errors
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(GateFailure("PHASE_EVIDENCE_READ", str(exc)).as_dict())
        return phase, errors
    phase["evidence"] = {
        "path": str(evidence_path.relative_to(snapshot_root)),
        "sha256": sha256_file(evidence_path),
        "method": evidence.get("method"),
    }
    # Source order, comments, symbol presence, and module load order are never
    # accepted as a callgraph proof.  Only the versioned binary method is
    # admissible, and it must bind exact main/report identities and site sets.
    if evidence.get("schema") != SCHEMA_PHASE or evidence.get("method") != "verified_binary_callgraph_v1":
        errors.append(GateFailure(
            "PHASE_EVIDENCE_METHOD",
            "prepare order requires verified_binary_callgraph_v1; source/comment ordering is insufficient",
            schema=evidence.get("schema"), method=evidence.get("method"),
        ).as_dict())
        return phase, errors
    if evidence.get("main_sha256") != main.sha256:
        errors.append(GateFailure("PHASE_EVIDENCE_MAIN_MISMATCH", "phase evidence binds another main ELF").as_dict())
        return phase, errors
    if evidence.get("prepare_symbol") not in symbols:
        errors.append(GateFailure("PHASE_EVIDENCE_PREPARE_SYMBOL", "phase evidence prepare symbol is not defined").as_dict())
        return phase, errors
    measured_sites = sorted(
        (item["sha256"], access["mrs_address"], access["address"], access["offset"], access["width"])
        for item in scan_objects for access in item["accesses"] if access["overlaps_slot5"]
    )
    reported_sites = sorted(
        (item.get("elf_sha256"), item.get("mrs_address"), item.get("access_address"), item.get("offset"), item.get("width"))
        for item in evidence.get("slot5_sites", []) if isinstance(item, dict)
    )
    if measured_sites != reported_sites:
        errors.append(GateFailure(
            "PHASE_EVIDENCE_SITE_SET_MISMATCH",
            "phase proof site set differs from exact scanner observations",
            measured=measured_sites, reported=reported_sites,
        ).as_dict())
        return phase, errors
    pre_count = evidence.get("pre_prepare_slot5_access_count")
    post_count = evidence.get("post_prepare_slot5_access_count")
    if not isinstance(pre_count, int) or not isinstance(post_count, int) or pre_count + post_count != len(measured_sites):
        errors.append(GateFailure("PHASE_EVIDENCE_COUNTS", "phase site counts are missing or inconsistent").as_dict())
        return phase, errors
    phase.update({
        "prepare_point_status": "BINARY_CALLGRAPH_BOUND",
        "prepare_order_proven": evidence.get("complete") is True,
        "pre_prepare": {"slot5_access_count": pre_count, "classification": "BINARY_CALLGRAPH"},
        "post_prepare": {"slot5_access_count": post_count, "classification": "BINARY_CALLGRAPH"},
        "unordered_relative_to_prepare": {"observed_slot5_access_count": 0},
    })
    if evidence.get("complete") is not True:
        errors.append(GateFailure("PHASE_EVIDENCE_INCOMPLETE", "binary callgraph proof is not complete").as_dict())
    if pre_count != 0:
        errors.append(GateFailure(
            "PRE_PREPARE_SLOT5_ACCESS",
            "at least one slot-5 access is reachable before prepare",
            pre_prepare_slot5_access_count=pre_count,
        ).as_dict())
    return phase, errors


def load_config(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        config = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateFailure("CONFIG_READ", str(exc), path=str(path)) from exc
    if config.get("schema") != SCHEMA_CONFIG:
        raise GateFailure("CONFIG_SCHEMA", "unsupported gate config schema", actual=config.get("schema"))
    return config, sha256_bytes(raw)


def checked_snapshot_path(snapshot_root: pathlib.Path, raw: Any, role: str, *, directory: bool = False) -> pathlib.Path:
    if not isinstance(raw, str) or pathlib.Path(raw).is_absolute():
        raise GateFailure("CONFIG_PATH", "snapshot paths must be non-empty relative strings", role=role, path=raw)
    candidate = snapshot_root / raw
    if candidate.is_symlink():
        raise GateFailure("SYMLINK_INPUT_FORBIDDEN", "snapshot input may not be a symlink", role=role, path=raw)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(snapshot_root)
    except ValueError as exc:
        raise GateFailure("SNAPSHOT_PATH_ESCAPE", "snapshot-relative path escapes root", role=role, path=raw) from exc
    if directory and not resolved.is_dir():
        raise GateFailure("SNAPSHOT_DIRECTORY", "snapshot search path is not a directory", role=role, path=raw)
    if not directory and not resolved.is_file():
        raise GateFailure("SNAPSHOT_FILE", "snapshot input is not a regular file", role=role, path=raw)
    return resolved


def identity_check(elf: Elf64, expected: Any, role: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(expected, dict):
        return [GateFailure("IDENTITY_CONFIG", "missing identity binding", role=role).as_dict()]
    if elf.sha256 != expected.get("sha256"):
        errors.append(GateFailure(
            "IDENTITY_SHA256", "ELF SHA differs from config binding", role=role, expected=expected.get("sha256"),
            actual=elf.sha256,
        ).as_dict())
    if elf.build_id != expected.get("build_id"):
        errors.append(GateFailure(
            "IDENTITY_BUILD_ID", "ELF Build-ID differs from config binding", role=role,
            expected=expected.get("build_id"), actual=elf.build_id,
        ).as_dict())
    return errors


def audit_tool_binding(config: dict[str, Any], snapshot_root: pathlib.Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    binding = config.get("tool_binding")
    if not isinstance(binding, dict):
        return {"valid": False}, [GateFailure(
            "TOOL_BINDING_MISSING", "certificate config must bind the exact frozen scanner/gate bytes"
        ).as_dict()]
    expected = binding.get("sha256")
    try:
        frozen = checked_snapshot_path(snapshot_root, binding.get("frozen_path"), "frozen_gate_tool")
    except GateFailure as exc:
        return {"valid": False}, [exc.as_dict()]
    running = pathlib.Path(__file__).resolve()
    frozen_sha = sha256_file(frozen)
    running_sha = sha256_file(running)
    valid = (
        isinstance(expected, str)
        and re.fullmatch(r"[0-9a-f]{64}", expected) is not None
        and frozen_sha == expected
        and running_sha == expected
    )
    audit = {
        "running_path": str(running.relative_to(PROJECT_ROOT)),
        "running_sha256": running_sha,
        "frozen_path": str(frozen.relative_to(snapshot_root)),
        "frozen_sha256": frozen_sha,
        "expected_sha256": expected,
        "valid": valid,
    }
    if not valid:
        errors.append(GateFailure(
            "TOOL_IDENTITY_MISMATCH",
            "running gate bytes and immutable frozen gate bytes must equal the config binding",
            **audit,
        ).as_dict())
    return audit, errors


def generate_certificate(config_path: pathlib.Path) -> dict[str, Any]:
    config_path = project_path(config_path, role="config", file=True)
    config, config_sha = load_config(config_path)
    snapshot_root = project_path(config.get("snapshot_root", ""), role="snapshot_root", directory=True)
    manifest_path = project_path(config.get("snapshot_manifest", ""), role="snapshot_manifest", file=True)
    errors: list[dict[str, Any]] = []
    snapshot_audit, manifest_errors = validate_snapshot_manifest(
        snapshot_root, manifest_path, str(config.get("snapshot_manifest_sha256", ""))
    )
    errors.extend(manifest_errors)
    tool_audit, tool_errors = audit_tool_binding(config, snapshot_root)
    errors.extend(tool_errors)

    try:
        main_path = checked_snapshot_path(snapshot_root, config.get("main"), "main")
        loader_path = checked_snapshot_path(snapshot_root, config.get("loader"), "loader")
        sidecar_path = checked_snapshot_path(snapshot_root, config.get("main_sidecar"), "main_sidecar")
        main = Elf64(main_path)
        loader = Elf64(loader_path)
        main_sidecar = Elf64(sidecar_path)
    except GateFailure as exc:
        errors.append(exc.as_dict())
        return {
            "schema": SCHEMA_CERTIFICATE,
            "status": "FAIL_CLOSED",
            "config": {"path": str(config_path.relative_to(PROJECT_ROOT)), "sha256": config_sha},
            "snapshot": snapshot_audit,
            "errors": errors,
        }
    errors.extend(identity_check(main, config.get("expected_main_identity"), "main"))
    errors.extend(identity_check(loader, config.get("expected_loader_identity"), "loader"))
    errors.extend(identity_check(main_sidecar, config.get("expected_main_sidecar_identity"), "main_sidecar"))
    if main.e_type != ET_DYN:
        errors.append(GateFailure("MAIN_NOT_PIE", "main ELF is not ET_DYN/PIE", elf_type=main.e_type).as_dict())
    sidecar = sidecar_audit(main, main_sidecar, snapshot_root)
    if not sidecar["valid"]:
        errors.append(GateFailure("MAIN_SIDECAR_MISMATCH", "main sidecar is not load-identical").as_dict())

    search_items = config.get("sealed_candidate_search_order")
    search_dirs: list[pathlib.Path] = []
    if not isinstance(search_items, list) or not search_items:
        errors.append(GateFailure("SEARCH_ORDER_EMPTY", "sealed candidate search order is empty").as_dict())
    else:
        for index, item in enumerate(search_items):
            try:
                if not isinstance(item, dict) or not isinstance(item.get("target"), str):
                    raise GateFailure("SEARCH_ORDER_FORMAT", "search item needs target and snapshot paths", index=index)
                search_dirs.append(checked_snapshot_path(
                    snapshot_root, item.get("snapshot"), f"search_order[{index}]", directory=True
                ))
            except GateFailure as exc:
                errors.append(exc.as_dict())
    search_evidence = parse_search_order_evidence(config, snapshot_root)
    if not search_evidence.get("proven"):
        errors.append(GateFailure(
            "PRODUCTION_SEARCH_ORDER_NOT_PROVEN",
            "sealed candidate resolution is not the exact production AArch64 loader order",
            reason=search_evidence.get("reason"),
            expected=search_evidence.get("expected_target_order"),
            observed=search_evidence.get("observed_target_order"),
        ).as_dict())

    resolver = Resolver(snapshot_root, loader, search_dirs)
    objects = resolver.resolve([(main, "initial_main")]) if search_dirs else [ClosureObject(main, "$MAIN", None, "initial_main")]
    errors.extend(resolver.errors)
    for obj in objects:
        if obj.elf.rpaths or obj.elf.runpaths:
            errors.append(GateFailure(
                "RPATH_RUNPATH_FORBIDDEN", "closure ELF contains load-path injection tags",
                path=str(obj.elf.path.relative_to(snapshot_root)), rpath=obj.elf.rpaths, runpath=obj.elf.runpaths,
            ).as_dict())
        if obj.elf.has_textrel:
            errors.append(GateFailure(
                "TEXTREL_FORBIDDEN", "closure ELF contains text relocations",
                path=str(obj.elf.path.relative_to(snapshot_root)),
            ).as_dict())

    pre_prepare_roots: list[ClosureObject] = []
    for index, item in enumerate(config.get("pre_prepare_runtime_roots", [])):
        try:
            path = checked_snapshot_path(snapshot_root, item.get("path") if isinstance(item, dict) else None,
                                         f"pre_prepare_runtime_roots[{index}]")
            elf = Elf64(path)
            pre_prepare_roots.append(ClosureObject(elf, elf.path.name, None, "pre_prepare_runtime_root_unordered"))
        except GateFailure as exc:
            errors.append(exc.as_dict())

    scan_unique: dict[pathlib.Path, ClosureObject] = {obj.elf.path: obj for obj in objects}
    for obj in pre_prepare_roots:
        scan_unique.setdefault(obj.elf.path, obj)
    slot = config.get("slot5") if isinstance(config.get("slot5"), dict) else {}
    slot_offset = int(slot.get("offset", 40))
    slot_width = int(slot.get("width", 8))
    window = int(config.get("tp_scan_window", 32))
    scan_reports = [
        scan_elf(obj.elf, snapshot_root, slot_offset, slot_width, window)
        | {"closure_category": obj.category}
        for obj in sorted(scan_unique.values(), key=lambda value: str(value.elf.path))
    ]
    tp_unknown = sum(item["unknown_count"] for item in scan_reports)
    if tp_unknown:
        errors.append(GateFailure(
            "TP_SCAN_UNKNOWN",
            "TP-derived flows remain unclassified; absence of a detected slot-5 site is not proof",
            unknown_tp_accesses=tp_unknown,
        ).as_dict())
    phase, phase_errors = evaluate_phase(config, main, main_sidecar, scan_reports, snapshot_root)
    errors.extend(phase_errors)
    pre_count = phase["pre_prepare"]["slot5_access_count"]
    if pre_count != 0:
        errors.append(GateFailure(
            "PRE_PREPARE_SLOT5_ZERO_NOT_PROVEN",
            "pre_prepare_slot5_access_count must be the integer zero from binary phase evidence",
            actual=pre_count,
        ).as_dict())

    initial_objects = [
        obj.elf.identity_dict(snapshot_root)
        | {"load_name": obj.load_name, "needed_by": obj.needed_by, "category": obj.category}
        for obj in objects
    ]
    # Every resolver-side error invalidates completeness.  Restricting this to
    # the common missing/ambiguous codes would accidentally let a malformed
    # provider, SONAME collision, or symlink candidate pass as a closed graph.
    unresolved = list(resolver.errors)
    closure_complete = not unresolved
    if not closure_complete:
        errors.append(GateFailure(
            "INITIAL_CLOSURE_INCOMPLETE",
            "recursive initial DT_NEEDED closure is incomplete or non-unique",
            unresolved_count=len(unresolved),
        ).as_dict())

    # Preserve first occurrence while making error order deterministic.
    seen_errors: set[str] = set()
    unique_errors: list[dict[str, Any]] = []
    for error in sorted(errors, key=lambda item: (str(item.get("code")), stable_json_bytes(item))):
        key = stable_json_bytes(error).decode("utf-8")
        if key not in seen_errors:
            seen_errors.add(key)
            unique_errors.append(error)

    certificate = {
        "schema": SCHEMA_CERTIFICATE,
        "status": "PASS" if not unique_errors else "FAIL_CLOSED",
        "claim_scope": {
            "proves_if_pass": [
                "exact project-local snapshot identity",
                "unique recursive initial DT_NEEDED resolution in exact production AArch64 order",
                "zero unknown TP-derived flows across resolved main/loader/closure",
                "binary-callgraph-proven prepare ordering and pre_prepare_slot5_access_count=0",
            ],
            "never_proves": [
                "production init execution",
                "SELinux Enforcing setcon success",
                "new-thread stack-guard initialization",
                "ActivityThread, Unity load, Surface present, or visible first frame",
            ],
        },
        "config": {"path": str(config_path.relative_to(PROJECT_ROOT)), "sha256": config_sha},
        "snapshot": snapshot_audit,
        "tool": tool_audit,
        "exact_subject": {
            "main": main.identity_dict(snapshot_root),
            "loader": loader.identity_dict(snapshot_root),
            "main_sidecar": sidecar,
        },
        "provider_resolution": {
            "production_search_order": search_evidence,
            "sealed_candidate_search_order": [
                {"target": item.get("target"), "snapshot": item.get("snapshot")} for item in search_items
            ] if isinstance(search_items, list) else [],
            "audits": resolver.audits,
            "complete_and_unique": closure_complete,
        },
        "initial_closure": {
            "complete": closure_complete,
            "object_count": len(initial_objects),
            "objects": initial_objects,
            "unresolved": unresolved,
        },
        "pre_prepare_runtime_roots": [
            obj.elf.identity_dict(snapshot_root) | {"classification": "UNORDERED_SOURCE_CANDIDATE"}
            for obj in pre_prepare_roots
        ],
        "tp_scan": {
            "method": "raw-aarch64-conservative-local-dataflow-v1",
            "method_limit": (
                "unmodelled, indirect, returned, or interprocedural TP provenance is counted unknown; "
                "zero detections cannot pass while any unknown remains"
            ),
            "window": window,
            "slot5": {"offset": slot_offset, "width": slot_width},
            "complete": tp_unknown == 0 and closure_complete,
            "unknown_tp_accesses": tp_unknown,
            "observed_slot5_access_count_unordered": sum(item["slot5_access_count"] for item in scan_reports),
            "objects": scan_reports,
        },
        "phase_partition": phase,
        "decision": {
            "pre_prepare_slot5_access_count": pre_count,
            "prepare_order_proven": phase["prepare_order_proven"],
            "eligible_for_product_tls_certificate": not unique_errors,
            "device_trial_authorized_by_this_gate": False,
        },
        "errors": unique_errors,
    }
    return certificate


def inventory_report(certificate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "westlake-initial-closure-inventory-v1",
        "status": certificate.get("status"),
        "config": certificate.get("config"),
        "snapshot": certificate.get("snapshot"),
        "exact_subject": certificate.get("exact_subject"),
        "provider_resolution": certificate.get("provider_resolution"),
        "initial_closure": certificate.get("initial_closure"),
        "pre_prepare_runtime_roots": certificate.get("pre_prepare_runtime_roots"),
    }


def tp_scan_report(certificate: dict[str, Any]) -> dict[str, Any]:
    closure_objects: list[dict[str, Any]] = []
    for item in certificate.get("initial_closure", {}).get("objects", []):
        module = item.get("load_name")
        if module == "$MAIN":
            module = "$MAIN"
        elif item.get("category") == "musl_loader":
            module = "$MUSL_LOADER"
        closure_objects.append({
            "module": module,
            "path": item.get("path"),
            "sha256": item.get("sha256"),
            "build_id": item.get("build_id"),
        })
    scan = certificate.get("tp_scan", {})
    phase = certificate.get("phase_partition", {})
    decision = certificate.get("decision", {})
    return {
        "schema": "westlake-initial-closure-tp-scan-v1",
        "complete": bool(
            scan.get("complete") is True
            and decision.get("prepare_order_proven") is True
            and decision.get("pre_prepare_slot5_access_count") == 0
        ),
        "unknown_tp_accesses": scan.get("unknown_tp_accesses"),
        "pre_prepare_slot5_access_count": decision.get("pre_prepare_slot5_access_count"),
        "prepare_order_proven": decision.get("prepare_order_proven"),
        "closure_objects": closure_objects,
        "provider_closure_complete": certificate.get("initial_closure", {}).get("complete"),
        "scan_method": scan.get("method"),
        "scan_method_limit": scan.get("method_limit"),
        "slot5": scan.get("slot5"),
        "observed_slot5_access_count_unordered": scan.get("observed_slot5_access_count_unordered"),
        "phase_partition": phase,
        "object_scans": scan.get("objects"),
        "config": certificate.get("config"),
        "snapshot": certificate.get("snapshot"),
    }


def command_manifest(args: argparse.Namespace) -> int:
    root = project_path(args.snapshot_root, role="snapshot_root", directory=True)
    output = project_path(args.output, role="manifest_output", must_exist=False)
    manifest = make_snapshot_manifest(root)
    write_atomic(output, stable_json_bytes(manifest))
    print(f"MANIFEST {sha256_file(output)} {output}")
    return 0


def command_certify(args: argparse.Namespace) -> int:
    certificate = generate_certificate(pathlib.Path(args.config))
    output = project_path(args.output, role="certificate_output", must_exist=False)
    write_atomic(output, stable_json_bytes(certificate))
    if args.inventory_report:
        inventory_path = project_path(args.inventory_report, role="inventory_report_output", must_exist=False)
        write_atomic(inventory_path, stable_json_bytes(inventory_report(certificate)))
    if args.tp_report:
        tp_path = project_path(args.tp_report, role="tp_report_output", must_exist=False)
        write_atomic(tp_path, stable_json_bytes(tp_scan_report(certificate)))
    print(f"{certificate['status']} {output}")
    return 0 if certificate["status"] == "PASS" else 1


def command_verify(args: argparse.Namespace) -> int:
    certificate_path = project_path(args.certificate, role="certificate", file=True)
    expected = stable_json_bytes(generate_certificate(pathlib.Path(args.config)))
    actual = certificate_path.read_bytes()
    if actual != expected:
        print("FAIL_CLOSED certificate bytes differ from a fresh deterministic rerun", file=sys.stderr)
        return 1
    decoded = json.loads(actual)
    print(f"REPRODUCIBLE_{decoded.get('status')} {certificate_path}")
    return 0 if decoded.get("status") == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    manifest = commands.add_parser("manifest")
    manifest.add_argument("--snapshot-root", required=True)
    manifest.add_argument("--output", required=True)
    manifest.set_defaults(func=command_manifest)
    certify = commands.add_parser("certify")
    certify.add_argument("--config", required=True)
    certify.add_argument("--output", required=True)
    certify.add_argument("--inventory-report")
    certify.add_argument("--tp-report")
    certify.set_defaults(func=command_certify)
    verify = commands.add_parser("verify")
    verify.add_argument("--config", required=True)
    verify.add_argument("--certificate", required=True)
    verify.set_defaults(func=command_verify)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return int(args.func(args))
    except GateFailure as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": exc.as_dict()}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
