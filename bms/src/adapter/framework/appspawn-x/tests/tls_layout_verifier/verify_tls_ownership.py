#!/usr/bin/env python3
"""Fail-closed verifier for OH musl/AArch64 initial TLS ownership.

This tool models the initial TLS allocation performed by the OpenHarmony musl
dynamic linker.  It deliberately does not execute the target ELF.  The result
is a generation-bound proof over an exact main executable, exact loader, exact
DT_NEEDED closure, and an explicit Bionic inline-slot inventory.

The implemented allocator is the TLS_ABOVE_TP branch in OH musl dynlink.c:

  main.offset = GAP_ABOVE_TP
  main.offset += (-GAP_ABOVE_TP + main.image) & (main.align - 1)
  next.offset = tls_offset
  next.offset += (-tls_offset + next.image) & (next.align - 1)

Runtime dlopen objects are never folded into the initial closure.  A newly
loaded PT_TLS object invalidates the generation instead.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import pathlib
import stat
import struct
import sys
import zipfile
from collections import deque
from typing import Any, Iterable, Optional


PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4
PT_TLS = 7

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
DT_RPATH = 15
DT_TEXTREL = 22
DT_FLAGS = 30
DT_RUNPATH = 29
DF_TEXTREL = 0x4

SHT_SYMTAB = 2
SHT_DYNSYM = 11
STT_TLS = 6

ET_EXEC = 2
ET_DYN = 3
EM_AARCH64 = 183

MUSL_RESERVED = {
    "libc.so",
    "libpthread.so",
    "librt.so",
    "libm.so",
    "libdl.so",
    "libutil.so",
    "libxnet.so",
}

# Product evidence is deliberately workspace-bound.  External paths may appear
# only as inert provenance labels in a frozen-input manifest; the verifier never
# reads them.  `resolve()` also prevents a symlink in the project from escaping
# this root.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[5]


class VerificationError(Exception):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            out["details"] = self.details
        return out


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def project_path(
    raw_path: pathlib.Path | str,
    *,
    role: str,
    must_exist: bool = True,
    regular_file: bool = False,
    directory: bool = False,
) -> pathlib.Path:
    """Resolve one verifier input and reject every path outside this project."""
    path = pathlib.Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        resolved = path.resolve(strict=must_exist)
    except OSError as exc:
        raise VerificationError(
            "PROJECT_INPUT_MISSING", "project-local verifier input cannot be resolved",
            role=role, path=str(path), error=str(exc),
        ) from exc
    try:
        resolved.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise VerificationError(
            "INPUT_OUTSIDE_PROJECT",
            "every verifier input/output must resolve inside the current project",
            role=role, path=str(path), resolved=str(resolved), project_root=str(PROJECT_ROOT),
        ) from exc
    if must_exist and regular_file and not resolved.is_file():
        raise VerificationError(
            "PROJECT_INPUT_NOT_FILE", "project-local input is not a regular file",
            role=role, path=str(resolved),
        )
    if must_exist and directory and not resolved.is_dir():
        raise VerificationError(
            "PROJECT_INPUT_NOT_DIRECTORY", "project-local input is not a directory",
            role=role, path=str(resolved),
        )
    return resolved


def is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


@dataclasses.dataclass(frozen=True)
class ProgramHeader:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int


@dataclasses.dataclass(frozen=True)
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


@dataclasses.dataclass(frozen=True)
class TlsSymbol:
    name: str
    value: int
    size: int
    binding: int
    visibility: int
    table: str

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


class ElfFile:
    """Small strict ELF64/LSB parser; target execution is never required."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path.resolve()
        try:
            fd = os.open(self.path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise VerificationError("ELF_NOT_REGULAR", "ELF input is not a regular file", path=str(path))
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
            raise VerificationError("ELF_READ_FAILED", str(exc), path=str(path)) from exc
        before_identity = (
            before.st_dev, before.st_ino, before.st_size,
            before.st_mtime_ns, before.st_ctime_ns,
        )
        after_identity = (
            after.st_dev, after.st_ino, after.st_size,
            after.st_mtime_ns, after.st_ctime_ns,
        )
        if before_identity != after_identity:
            raise VerificationError(
                "ELF_CHANGED_DURING_READ", "ELF metadata changed while it was being read",
                path=str(path), before=before_identity, after=after_identity,
            )
        self.data = b"".join(chunks)
        if len(self.data) != before.st_size:
            raise VerificationError(
                "ELF_SHORT_READ", "ELF byte count differs from fstat size",
                path=str(path), read_size=len(self.data), stat_size=before.st_size,
            )
        self.file_identity = (before.st_dev, before.st_ino)
        self.file_stat = {
            "device": before.st_dev,
            "inode": before.st_ino,
            "size": before.st_size,
            "mtime_ns": before.st_mtime_ns,
            "ctime_ns": before.st_ctime_ns,
        }
        if len(self.data) < 64 or self.data[:4] != b"\x7fELF":
            raise VerificationError("NOT_ELF", "input is not an ELF file", path=str(path))
        if self.data[4] != 2:
            raise VerificationError("ELF_CLASS", "only ELF64 is accepted", path=str(path), elf_class=self.data[4])
        if self.data[5] != 1:
            raise VerificationError("ELF_ENDIAN", "only little-endian ELF is accepted", path=str(path), data=self.data[5])
        if self.data[6] != 1:
            raise VerificationError("ELF_VERSION", "unsupported ELF version", path=str(path), version=self.data[6])

        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        (
            _, self.e_type, self.e_machine, self.e_version, self.e_entry,
            self.e_phoff, self.e_shoff, self.e_flags, self.e_ehsize,
            self.e_phentsize, self.e_phnum, self.e_shentsize, self.e_shnum,
            self.e_shstrndx,
        ) = header
        if self.e_phnum and self.e_phentsize < 56:
            raise VerificationError("ELF_PHENTSIZE", "program header entry is truncated", path=str(path))
        if self.e_shnum and self.e_shentsize < 64:
            raise VerificationError("ELF_SHENTSIZE", "section header entry is truncated", path=str(path))

        self.program_headers = self._parse_program_headers()
        self.section_headers = self._parse_section_headers()
        self.dynamic = self._parse_dynamic()
        self.needed = [self._dynamic_string(v) for t, v in self.dynamic if t == DT_NEEDED]
        duplicate_needed = sorted({name for name in self.needed if self.needed.count(name) > 1})
        if duplicate_needed:
            raise VerificationError(
                "DUPLICATE_DT_NEEDED", "an ELF contains duplicate DT_NEEDED names",
                path=str(self.path), names=duplicate_needed,
            )
        self.soname = self._last_dynamic_string(DT_SONAME)
        self.rpaths = [self._dynamic_string(value) for tag, value in self.dynamic if tag == DT_RPATH]
        self.runpaths = [self._dynamic_string(value) for tag, value in self.dynamic if tag == DT_RUNPATH]
        self.rpath = self.runpaths[-1] if self.runpaths else (self.rpaths[-1] if self.rpaths else None)
        self.has_textrel = any(
            tag == DT_TEXTREL or (tag == DT_FLAGS and bool(value & DF_TEXTREL))
            for tag, value in self.dynamic
        )
        self.tls = self._parse_tls_segment()
        self.tls_symbols = self._parse_tls_symbols()
        self.build_id = self._parse_build_id()
        self.sha256 = hashlib.sha256(self.data).hexdigest()

    def _require_range(self, offset: int, size: int, what: str) -> None:
        if offset < 0 or size < 0 or offset > len(self.data) or size > len(self.data) - offset:
            raise VerificationError(
                "ELF_RANGE", f"{what} lies outside file", path=str(self.path), offset=offset, size=size,
                file_size=len(self.data),
            )

    def _parse_program_headers(self) -> list[ProgramHeader]:
        out: list[ProgramHeader] = []
        if self.e_phnum:
            self._require_range(self.e_phoff, self.e_phentsize * self.e_phnum, "program header table")
        for index in range(self.e_phnum):
            off = self.e_phoff + index * self.e_phentsize
            out.append(ProgramHeader(*struct.unpack_from("<IIQQQQQQ", self.data, off)))
        return out

    def _parse_section_headers(self) -> list[SectionHeader]:
        out: list[SectionHeader] = []
        if self.e_shnum:
            self._require_range(self.e_shoff, self.e_shentsize * self.e_shnum, "section header table")
        for index in range(self.e_shnum):
            off = self.e_shoff + index * self.e_shentsize
            out.append(SectionHeader(*struct.unpack_from("<IIQQQQIIQQ", self.data, off)))
        return out

    def _vaddr_to_offset(self, vaddr: int, size: int = 1) -> int:
        for ph in self.program_headers:
            if ph.p_type != PT_LOAD:
                continue
            if ph.p_vaddr <= vaddr and size <= ph.p_filesz and vaddr - ph.p_vaddr <= ph.p_filesz - size:
                return ph.p_offset + (vaddr - ph.p_vaddr)
        raise VerificationError(
            "ELF_VADDR_UNMAPPED", "virtual address is not backed by file bytes",
            path=str(self.path), vaddr=vaddr, size=size,
        )

    def _parse_dynamic(self) -> list[tuple[int, int]]:
        segments = [ph for ph in self.program_headers if ph.p_type == PT_DYNAMIC]
        if len(segments) > 1:
            raise VerificationError("MULTIPLE_PT_DYNAMIC", "more than one PT_DYNAMIC", path=str(self.path))
        if not segments:
            return []
        seg = segments[0]
        if seg.p_filesz % 16:
            raise VerificationError("DYNAMIC_SIZE", "PT_DYNAMIC size is not an Elf64_Dyn multiple", path=str(self.path))
        self._require_range(seg.p_offset, seg.p_filesz, "PT_DYNAMIC")
        out: list[tuple[int, int]] = []
        saw_null = False
        for off in range(seg.p_offset, seg.p_offset + seg.p_filesz, 16):
            tag, value = struct.unpack_from("<QQ", self.data, off)
            out.append((tag, value))
            if tag == DT_NULL:
                saw_null = True
                break
        if not saw_null:
            raise VerificationError("DYNAMIC_NO_NULL", "PT_DYNAMIC has no DT_NULL terminator", path=str(self.path))
        return out

    def _dynamic_strtab(self) -> tuple[int, int]:
        strtabs = [v for t, v in self.dynamic if t == DT_STRTAB]
        sizes = [v for t, v in self.dynamic if t == DT_STRSZ]
        if len(strtabs) != 1 or len(sizes) != 1:
            raise VerificationError(
                "DYNAMIC_STRTAB", "dynamic string table is missing or ambiguous", path=str(self.path),
                strtab_count=len(strtabs), strsz_count=len(sizes),
            )
        return self._vaddr_to_offset(strtabs[0], sizes[0]), sizes[0]

    def _dynamic_string(self, index: int) -> str:
        base, size = self._dynamic_strtab()
        if index >= size:
            raise VerificationError("DYNAMIC_STRING_INDEX", "dynamic string index out of range", path=str(self.path), index=index)
        end = self.data.find(b"\0", base + index, base + size)
        if end < 0:
            raise VerificationError("DYNAMIC_STRING_NUL", "unterminated dynamic string", path=str(self.path), index=index)
        return self.data[base + index:end].decode("utf-8", errors="strict")

    def _last_dynamic_string(self, tag: int) -> Optional[str]:
        values = [v for t, v in self.dynamic if t == tag]
        return self._dynamic_string(values[-1]) if values else None

    def _effective_rpath(self) -> Optional[str]:
        runpaths = [v for t, v in self.dynamic if t == DT_RUNPATH]
        rpaths = [v for t, v in self.dynamic if t == DT_RPATH]
        values = runpaths if runpaths else rpaths
        return self._dynamic_string(values[-1]) if values else None

    def _parse_tls_segment(self) -> Optional[ProgramHeader]:
        segments = [ph for ph in self.program_headers if ph.p_type == PT_TLS]
        if len(segments) > 1:
            raise VerificationError("MULTIPLE_PT_TLS", "more than one PT_TLS", path=str(self.path))
        if not segments:
            return None
        tls = segments[0]
        if tls.p_filesz > tls.p_memsz:
            raise VerificationError("PT_TLS_FILESZ", "PT_TLS filesz exceeds memsz", path=str(self.path))
        align = max(tls.p_align, 1)
        if not is_power_of_two(align):
            raise VerificationError("PT_TLS_ALIGN", "PT_TLS alignment is not a power of two", path=str(self.path), align=align)
        if tls.p_filesz:
            self._require_range(tls.p_offset, tls.p_filesz, "PT_TLS image")
        if (tls.p_vaddr - tls.p_offset) & (align - 1):
            raise VerificationError(
                "PT_TLS_CONGRUENCE", "PT_TLS vaddr/file offset violate alignment congruence",
                path=str(self.path), vaddr=tls.p_vaddr, offset=tls.p_offset, align=align,
            )
        load_aligns = [max(ph.p_align, 1) for ph in self.program_headers if ph.p_type == PT_LOAD]
        if not load_aligns:
            raise VerificationError("NO_PT_LOAD", "ELF has PT_TLS but no PT_LOAD", path=str(self.path))
        max_load_align = max(load_aligns)
        if max_load_align % align:
            raise VerificationError(
                "LOAD_BIAS_ALIGNMENT_UNPROVEN",
                "PT_LOAD alignment cannot prove runtime TLS image residue",
                path=str(self.path), tls_align=align, max_load_align=max_load_align,
            )
        return tls

    def _parse_tls_symbols(self) -> list[TlsSymbol]:
        out: list[TlsSymbol] = []
        for section_index, sh in enumerate(self.section_headers):
            if sh.sh_type not in (SHT_SYMTAB, SHT_DYNSYM):
                continue
            if sh.sh_link >= len(self.section_headers):
                raise VerificationError("SYMTAB_LINK", "symbol table string link out of range", path=str(self.path))
            strings = self.section_headers[sh.sh_link]
            self._require_range(strings.sh_offset, strings.sh_size, "symbol string table")
            entsize = sh.sh_entsize or 24
            if entsize < 24 or sh.sh_size % entsize:
                raise VerificationError("SYMTAB_SIZE", "invalid Elf64_Sym table size", path=str(self.path), section=section_index)
            self._require_range(sh.sh_offset, sh.sh_size, "symbol table")
            table_name = ".dynsym" if sh.sh_type == SHT_DYNSYM else ".symtab"
            for off in range(sh.sh_offset, sh.sh_offset + sh.sh_size, entsize):
                name_idx, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", self.data, off)
                if (info & 0x0F) != STT_TLS or shndx == 0:
                    continue
                if name_idx >= strings.sh_size:
                    raise VerificationError("SYMBOL_NAME_INDEX", "TLS symbol name index out of range", path=str(self.path))
                start = strings.sh_offset + name_idx
                end = self.data.find(b"\0", start, strings.sh_offset + strings.sh_size)
                if end < 0:
                    raise VerificationError("SYMBOL_NAME_NUL", "unterminated TLS symbol name", path=str(self.path))
                name = self.data[start:end].decode("utf-8", errors="strict")
                out.append(TlsSymbol(name, value, size, info >> 4, other & 0x03, table_name))
        # A symbol may be present in both .dynsym and .symtab.  Keep one exact
        # record and retain genuinely conflicting records for ambiguity checks.
        unique: dict[tuple[str, int, int, int, int], TlsSymbol] = {}
        for symbol in out:
            key = (symbol.name, symbol.value, symbol.size, symbol.binding, symbol.visibility)
            old = unique.get(key)
            if old is None or (old.table == ".dynsym" and symbol.table == ".symtab"):
                unique[key] = symbol
        return sorted(unique.values(), key=lambda s: (s.value, s.name, s.size, s.table))

    def _parse_build_id(self) -> Optional[str]:
        for ph in self.program_headers:
            if ph.p_type != PT_NOTE or not ph.p_filesz:
                continue
            self._require_range(ph.p_offset, ph.p_filesz, "PT_NOTE")
            off = ph.p_offset
            end = ph.p_offset + ph.p_filesz
            while off + 12 <= end:
                namesz, descsz, note_type = struct.unpack_from("<III", self.data, off)
                off += 12
                name_end = off + namesz
                desc_off = (name_end + 3) & ~3
                desc_end = desc_off + descsz
                next_off = (desc_end + 3) & ~3
                if next_off > end:
                    raise VerificationError("NOTE_RANGE", "truncated ELF note", path=str(self.path))
                name = self.data[off:name_end].rstrip(b"\0")
                if name == b"GNU" and note_type == 3:
                    return self.data[desc_off:desc_end].hex()
                off = next_off
        return None

    def identity(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "build_id": self.build_id,
            "elf_type": self.e_type,
            "machine": self.e_machine,
            "soname": self.soname,
            "needed": self.needed,
            "rpath": self.rpath,
            "rpaths": self.rpaths,
            "runpaths": self.runpaths,
            "has_textrel": self.has_textrel,
            "file_stat": self.file_stat,
        }


@dataclasses.dataclass
class LoadedObject:
    elf: ElfFile
    requested_as: str
    needed_by: Optional[str]
    shortname: Optional[str]
    is_main: bool = False
    is_loader: bool = False
    tls_offset: Optional[int] = None
    symbol_sidecar: Optional[ElfFile] = None

    def module_name(self) -> str:
        if self.is_main:
            return "$MAIN"
        if self.is_loader:
            return "$MUSL_LOADER"
        return self.shortname or self.elf.soname or self.elf.path.name


class ClosureResolver:
    def __init__(
        self,
        main: ElfFile,
        loader: Optional[ElfFile],
        env_dirs: list[pathlib.Path],
        system_dirs: list[pathlib.Path],
        rootfs: Optional[pathlib.Path],
        cwd: pathlib.Path,
    ) -> None:
        self.main = main
        self.loader = loader
        self.env_dirs = [p.resolve() for p in env_dirs]
        self.system_dirs = [p.resolve() for p in system_dirs]
        self.rootfs = rootfs.resolve() if rootfs else None
        self.cwd = cwd.resolve()
        self.errors: list[VerificationError] = []
        self.resolution_audit: list[dict[str, Any]] = []

    @staticmethod
    def _identity(path: pathlib.Path) -> tuple[int, int]:
        st = path.stat()
        return st.st_dev, st.st_ino

    def _map_absolute(self, path: pathlib.Path) -> pathlib.Path:
        if path.is_absolute() and self.rootfs:
            return self.rootfs / str(path).lstrip("/")
        return path

    def _expand_rpath(self, obj: LoadedObject) -> list[pathlib.Path]:
        raw = obj.elf.rpath
        if not raw:
            return []
        raise VerificationError(
            "RPATH_RUNPATH_FORBIDDEN",
            "DT_RPATH/DT_RUNPATH is forbidden in a certifiable generation",
            path=str(obj.elf.path), rpaths=obj.elf.rpaths, runpaths=obj.elf.runpaths,
        )

    def _search_chain(self, needed_by: LoadedObject, chain_by_path: dict[pathlib.Path, LoadedObject]) -> list[pathlib.Path]:
        out = list(self.env_dirs)
        current: Optional[LoadedObject] = needed_by
        seen: set[pathlib.Path] = set()
        while current is not None and current.elf.path not in seen:
            seen.add(current.elf.path)
            out.extend(self._expand_rpath(current))
            if current.needed_by is None:
                current = None
            else:
                current = chain_by_path.get(pathlib.Path(current.needed_by))
        out.extend(self.system_dirs)
        # Preserve real loader order.  Repeated directory entries are harmless.
        return out

    def _resolve_bare(
        self, name: str, needed_by: LoadedObject, chain_by_path: dict[pathlib.Path, LoadedObject]
    ) -> pathlib.Path:
        dirs = self._search_chain(needed_by, chain_by_path)
        candidates: list[pathlib.Path] = []
        for directory in dirs:
            path = directory / name
            if path.exists():
                if not path.is_file():
                    raise VerificationError("NEEDED_NOT_FILE", "DT_NEEDED candidate is not a regular file", path=str(path))
                candidates.append(path.resolve())
        identities: dict[tuple[int, int], list[str]] = {}
        for path in candidates:
            identities.setdefault(self._identity(path), []).append(str(path))
        audit = {
            "needed": name,
            "needed_by": str(needed_by.elf.path),
            "search_dirs": [str(p) for p in dirs],
            "candidates": [str(p) for p in candidates],
            "distinct_file_identities": len(identities),
        }
        self.resolution_audit.append(audit)
        if not identities:
            raise VerificationError(
                "NEEDED_NOT_FOUND", "DT_NEEDED could not be resolved from the sealed search path",
                needed=name, needed_by=str(needed_by.elf.path), search_dirs=audit["search_dirs"],
            )
        if len(identities) != 1:
            raise VerificationError(
                "NEEDED_SEARCH_AMBIGUITY", "DT_NEEDED name resolves to more than one file identity",
                needed=name, needed_by=str(needed_by.elf.path), candidates=audit["candidates"],
            )
        return pathlib.Path(next(iter(identities.values()))[0])

    def _resolve_needed(
        self, name: str, needed_by: LoadedObject, chain_by_path: dict[pathlib.Path, LoadedObject]
    ) -> pathlib.Path:
        if "/" not in name:
            return self._resolve_bare(name, needed_by, chain_by_path)
        path = pathlib.Path(name)
        path = self._map_absolute(path)
        if not path.is_absolute():
            path = self.cwd / path
        path = path.resolve()
        self.resolution_audit.append({
            "needed": name,
            "needed_by": str(needed_by.elf.path),
            "explicit_path": str(path),
        })
        if not path.is_file():
            raise VerificationError(
                "NEEDED_EXPLICIT_NOT_FOUND", "explicit DT_NEEDED path is not a file",
                needed=name, needed_by=str(needed_by.elf.path), path=str(path),
            )
        return path

    def resolve_initial(self) -> list[LoadedObject]:
        main_obj = LoadedObject(self.main, str(self.main.path), None, None, is_main=True)
        chain: list[LoadedObject] = [main_obj]
        chain_by_path: dict[pathlib.Path, LoadedObject] = {self.main.path: main_obj}
        loaded_by_inode: dict[tuple[int, int], LoadedObject] = {self.main.file_identity: main_obj}
        loaded_by_shortname: dict[str, LoadedObject] = {}
        loader_obj: Optional[LoadedObject] = None

        index = 0
        while index < len(chain):
            current = chain[index]
            index += 1
            if current.is_loader:
                continue
            for needed in current.elf.needed:
                if needed in MUSL_RESERVED:
                    if self.loader is None:
                        self.errors.append(VerificationError(
                            "MUSL_LOADER_REQUIRED",
                            "a musl-reserved DT_NEEDED requires --loader identity",
                            needed=needed, needed_by=str(current.elf.path),
                        ))
                        continue
                    if loader_obj is None:
                        loader_obj = LoadedObject(
                            self.loader, needed, str(current.elf.path), "libc.so", is_loader=True,
                        )
                        chain.append(loader_obj)
                        chain_by_path[self.loader.path] = loader_obj
                        loaded_by_inode[self.loader.file_identity] = loader_obj
                        for reserved in MUSL_RESERVED:
                            loaded_by_shortname[reserved] = loader_obj
                    continue

                # Audit the sealed search set even if musl would reuse an earlier
                # shortname.  Multiple file identities are not certifiable.
                try:
                    path = self._resolve_needed(needed, current, chain_by_path)
                except VerificationError as exc:
                    self.errors.append(exc)
                    continue

                if "/" not in needed and needed in loaded_by_shortname:
                    prior = loaded_by_shortname[needed]
                    if self._identity(path) != prior.elf.file_identity:
                        self.errors.append(VerificationError(
                            "LOADED_SHORTNAME_IDENTITY_MISMATCH",
                            "loaded shortname and sealed search resolve to different file identities",
                            needed=needed, loaded=str(prior.elf.path), searched=str(path),
                        ))
                    continue

                preopen_inode = self._identity(path)
                if preopen_inode in loaded_by_inode:
                    prior = loaded_by_inode[preopen_inode]
                    if "/" not in needed:
                        loaded_by_shortname[needed] = prior
                    continue
                try:
                    elf = ElfFile(path)
                except VerificationError as exc:
                    self.errors.append(exc)
                    continue
                if elf.file_identity != preopen_inode:
                    self.errors.append(VerificationError(
                        "NEEDED_CHANGED_BEFORE_READ",
                        "resolved DT_NEEDED file identity changed before its stable read",
                        path=str(path), resolved_identity=preopen_inode,
                        read_identity=elf.file_identity,
                    ))
                    continue
                obj = LoadedObject(
                    elf, needed, str(current.elf.path), needed if "/" not in needed else None,
                )
                chain.append(obj)
                chain_by_path[path] = obj
                loaded_by_inode[elf.file_identity] = obj
                if obj.shortname:
                    loaded_by_shortname[obj.shortname] = obj

        return chain


def attach_symbol_sidecars(
    chain: list[LoadedObject], specs: list[str], expected_machine: int,
    errors: list[VerificationError],
) -> list[dict[str, Any]]:
    """Attach unstripped symbol evidence without replacing final ELF identity."""
    audit: list[dict[str, Any]] = []
    seen_modules: set[str] = set()
    for spec in specs:
        if "=" not in spec:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_SPEC", "symbol sidecar must be MODULE=PATH", spec=spec,
            ))
            continue
        module_name, raw_path = spec.split("=", 1)
        if not module_name or not raw_path or module_name in seen_modules:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_SPEC", "symbol sidecar module/path is empty or duplicated", spec=spec,
            ))
            continue
        seen_modules.add(module_name)
        modules = find_modules(chain, module_name)
        if len(modules) != 1:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_MODULE_AMBIGUOUS" if modules else "SYMBOL_SIDECAR_MODULE_MISSING",
                "symbol sidecar target module must resolve exactly once",
                module=module_name, matches=[str(obj.elf.path) for obj in modules],
            ))
            continue
        obj = modules[0]
        try:
            sidecar_path = project_path(
                raw_path, role=f"symbol_sidecar:{module_name}", regular_file=True,
            )
            sidecar = ElfFile(sidecar_path)
        except VerificationError as exc:
            errors.append(exc)
            continue
        item = {
            "module": module_name,
            "final_path": str(obj.elf.path),
            "final_sha256": obj.elf.sha256,
            "final_build_id": obj.elf.build_id,
            "sidecar_path": str(sidecar.path),
            "sidecar_sha256": sidecar.sha256,
            "sidecar_build_id": sidecar.build_id,
        }
        audit.append(item)
        if sidecar.rpaths or sidecar.runpaths:
            errors.append(VerificationError(
                "RPATH_RUNPATH_FORBIDDEN", "symbol sidecar contains DT_RPATH/DT_RUNPATH", **item,
                rpaths=sidecar.rpaths, runpaths=sidecar.runpaths,
            ))
            continue
        if sidecar.has_textrel:
            errors.append(VerificationError(
                "TEXTREL_FORBIDDEN", "symbol sidecar contains DT_TEXTREL/DF_TEXTREL", **item,
            ))
            continue
        if sidecar.e_machine != expected_machine or sidecar.e_machine != obj.elf.e_machine:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_MACHINE", "symbol sidecar machine differs from final ELF",
                **item, sidecar_machine=sidecar.e_machine, final_machine=obj.elf.e_machine,
            ))
            continue
        if not obj.elf.build_id or not sidecar.build_id or obj.elf.build_id != sidecar.build_id:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_BUILD_ID", "symbol sidecar must have the same non-empty Build-ID as final ELF",
                **item,
            ))
            continue
        def load_fingerprint(elf: ElfFile) -> list[tuple[int, int, int, int, int, int, str]]:
            fingerprint: list[tuple[int, int, int, int, int, int, str]] = []
            for ph in elf.program_headers:
                # A normal strip may rewrite the read-only dynsym/hash load.
                # Executable and writable loads, however, must remain exact.
                if ph.p_type != PT_LOAD or not (ph.p_flags & (1 | 2)):
                    continue
                segment_hash = hashlib.sha256(
                    elf.data[ph.p_offset:ph.p_offset + ph.p_filesz]
                ).hexdigest()
                fingerprint.append((
                    ph.p_offset, ph.p_vaddr, ph.p_filesz, ph.p_memsz,
                    ph.p_flags, max(ph.p_align, 1), segment_hash,
                ))
            return fingerprint
        final_loads = load_fingerprint(obj.elf)
        side_loads = load_fingerprint(sidecar)
        if obj.elf.e_type != sidecar.e_type or obj.elf.e_entry != sidecar.e_entry or final_loads != side_loads:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_LOAD_SEGMENTS",
                "unstripped sidecar must have byte-identical executable/writable PT_LOAD segments and ELF entry/type",
                **item, final_load_segments=final_loads, sidecar_load_segments=side_loads,
            ))
            continue
        final_tls = obj.elf.tls
        side_tls = sidecar.tls
        final_tuple = None if final_tls is None else (
            final_tls.p_offset, final_tls.p_vaddr, final_tls.p_filesz,
            final_tls.p_memsz, max(final_tls.p_align, 1),
        )
        side_tuple = None if side_tls is None else (
            side_tls.p_offset, side_tls.p_vaddr, side_tls.p_filesz,
            side_tls.p_memsz, max(side_tls.p_align, 1),
        )
        if final_tuple != side_tuple:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_PT_TLS", "symbol sidecar PT_TLS differs from final ELF",
                **item, final_pt_tls=final_tuple, sidecar_pt_tls=side_tuple,
            ))
            continue
        if obj.elf.needed != sidecar.needed or obj.elf.soname != sidecar.soname:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_DYNAMIC_IDENTITY",
                "symbol sidecar DT_NEEDED/SONAME differs from final ELF",
                **item, final_needed=obj.elf.needed, sidecar_needed=sidecar.needed,
                final_soname=obj.elf.soname, sidecar_soname=sidecar.soname,
            ))
            continue
        if not sidecar.tls_symbols:
            errors.append(VerificationError(
                "SYMBOL_SIDECAR_NO_TLS_SYMBOLS", "symbol sidecar supplies no TLS symbols", **item,
            ))
            continue
        obj.symbol_sidecar = sidecar
    return audit


def audit_closure_name_collisions(
    chain: list[LoadedObject], errors: list[VerificationError]
) -> list[dict[str, Any]]:
    """Reject different files claiming the same load-visible name/SONAME."""
    claims: dict[str, list[LoadedObject]] = {}
    for obj in chain:
        if obj.is_main or obj.is_loader:
            continue
        names = {obj.elf.path.name}
        if obj.shortname:
            names.add(obj.shortname)
        if obj.elf.soname:
            names.add(obj.elf.soname)
        for name in names:
            claims.setdefault(name, []).append(obj)
    audit: list[dict[str, Any]] = []
    for name, objects in sorted(claims.items()):
        identities: dict[tuple[int, int], list[LoadedObject]] = {}
        for obj in objects:
            identities.setdefault(obj.elf.file_identity, []).append(obj)
        item = {
            "name": name,
            "paths": sorted({str(obj.elf.path) for obj in objects}),
            "distinct_file_identities": len(identities),
        }
        audit.append(item)
        if len(identities) > 1:
            errors.append(VerificationError(
                "CLOSURE_NAME_COLLISION",
                "different closure objects claim the same basename/shortname/SONAME",
                **item,
            ))
    return audit


def audit_loaded_elf_policy(
    objects: Iterable[LoadedObject], errors: list[VerificationError], *, scope: str,
) -> list[dict[str, Any]]:
    """Reject load-path injection and text relocations for every loaded byte."""
    audit: list[dict[str, Any]] = []
    seen: set[pathlib.Path] = set()
    for obj in objects:
        if obj.elf.path in seen:
            continue
        seen.add(obj.elf.path)
        item = {
            "scope": scope,
            "path": str(obj.elf.path),
            "sha256": obj.elf.sha256,
            "rpaths": obj.elf.rpaths,
            "runpaths": obj.elf.runpaths,
            "has_textrel": obj.elf.has_textrel,
        }
        audit.append(item)
        if obj.elf.rpaths or obj.elf.runpaths:
            errors.append(VerificationError(
                "RPATH_RUNPATH_FORBIDDEN",
                "loaded ELF contains DT_RPATH or DT_RUNPATH",
                **item,
            ))
        if obj.elf.has_textrel:
            errors.append(VerificationError(
                "TEXTREL_FORBIDDEN", "loaded ELF contains DT_TEXTREL/DF_TEXTREL", **item,
            ))
    return audit


def module_tls_dict(obj: LoadedObject) -> Optional[dict[str, Any]]:
    tls = obj.elf.tls
    if tls is None or obj.tls_offset is None:
        return None
    symbol_source = obj.symbol_sidecar or obj.elf
    return {
        "p_offset": tls.p_offset,
        "p_vaddr": tls.p_vaddr,
        "p_filesz": tls.p_filesz,
        "p_memsz": tls.p_memsz,
        "p_align": max(tls.p_align, 1),
        "tls_offset_from_tp": obj.tls_offset,
        "owned_tp_range": [obj.tls_offset, obj.tls_offset + tls.p_memsz - 1] if tls.p_memsz else [],
        "symbol_evidence": {
            "path": str(symbol_source.path),
            "sha256": symbol_source.sha256,
            "build_id": symbol_source.build_id,
            "is_unstripped_sidecar": obj.symbol_sidecar is not None,
        },
        "symbols": [symbol.as_dict() for symbol in symbol_source.tls_symbols],
    }


def compute_initial_tls_layout(
    chain: list[LoadedObject], gap_above_tp: int, errors: list[VerificationError]
) -> tuple[list[LoadedObject], int]:
    tls_offset = 0
    tls_objects: list[LoadedObject] = []
    main = chain[0]
    if main.elf.tls is not None and main.elf.tls.p_memsz:
        tls = main.elf.tls
        align = max(tls.p_align, 1)
        main.tls_offset = gap_above_tp + ((-gap_above_tp + tls.p_vaddr) & (align - 1))
        tls_offset = main.tls_offset + tls.p_memsz
        tls_objects.append(main)

    for obj in chain[1:]:
        # musl's own loader/libc DSO is a stage-2 object, not a tls_module in
        # the initial application list.  Its pthread/errno state is outside the
        # positive-offset module allocation modeled here.
        if obj.is_loader or obj.elf.tls is None or not obj.elf.tls.p_memsz:
            continue
        tls = obj.elf.tls
        align = max(tls.p_align, 1)
        obj.tls_offset = tls_offset + ((-tls_offset + tls.p_vaddr) & (align - 1))
        tls_offset = obj.tls_offset + tls.p_memsz
        tls_objects.append(obj)

    previous_end = 0
    for obj in sorted(tls_objects, key=lambda item: item.tls_offset or 0):
        assert obj.tls_offset is not None and obj.elf.tls is not None
        if obj.tls_offset < previous_end:
            errors.append(VerificationError(
                "TLS_MODULE_OVERLAP", "computed TLS modules overlap",
                module=obj.module_name(), offset=obj.tls_offset, previous_end=previous_end,
            ))
        previous_end = max(previous_end, obj.tls_offset + obj.elf.tls.p_memsz)
    return tls_objects, tls_offset


def owner_for_byte(tls_objects: list[LoadedObject], offset: int) -> Optional[LoadedObject]:
    owners: list[LoadedObject] = []
    for obj in tls_objects:
        assert obj.tls_offset is not None and obj.elf.tls is not None
        if obj.tls_offset <= offset < obj.tls_offset + obj.elf.tls.p_memsz:
            owners.append(obj)
    if len(owners) > 1:
        raise VerificationError(
            "TLS_BYTE_MULTI_OWNER", "a TP-relative byte has multiple module owners",
            offset=offset, owners=[owner.module_name() for owner in owners],
        )
    return owners[0] if owners else None


def compressed_owner_ranges(tls_objects: list[LoadedObject], limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    ranges: list[dict[str, Any]] = []
    start = 0
    last_owner = owner_for_byte(tls_objects, 0)
    for offset in range(1, limit + 1):
        owner = owner_for_byte(tls_objects, offset) if offset < limit else None
        if offset == limit or owner is not last_owner:
            ranges.append({
                "tp_range": [start, offset - 1],
                "owner_kind": "module" if last_owner else "loader_alignment_gap",
                "owner": last_owner.module_name() if last_owner else None,
                "path": str(last_owner.elf.path) if last_owner else None,
            })
            start = offset
            last_owner = owner
    return ranges


def find_modules(chain: list[LoadedObject], name: str) -> list[LoadedObject]:
    matches: list[LoadedObject] = []
    for obj in chain:
        names = {obj.module_name(), obj.elf.path.name}
        if obj.elf.soname:
            names.add(obj.elf.soname)
        if name in names:
            matches.append(obj)
    return matches


def exact_tls_symbols(obj: LoadedObject, name: str) -> list[TlsSymbol]:
    source = obj.symbol_sidecar or obj.elf
    return [symbol for symbol in source.tls_symbols if symbol.name == name]


def evaluate_inventory(
    config: dict[str, Any], chain: list[LoadedObject], tls_objects: list[LoadedObject],
    errors: list[VerificationError],
) -> tuple[Optional[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    host_ranges: list[tuple[int, int, str]] = []
    for owner in config.get("host_tp_owners", []):
        if not isinstance(owner, dict):
            continue
        try:
            owner_offset = int(owner.get("offset"))
            owner_width = int(owner.get("width"))
        except (TypeError, ValueError):
            continue
        if owner_width > 0:
            host_ranges.append((owner_offset, owner_offset + owner_width, str(owner.get("id"))))
    host_byte_claims: dict[int, str] = {}
    for start, end, owner_id in host_ranges:
        for byte in range(start, end):
            if byte in host_byte_claims:
                errors.append(VerificationError(
                    "HOST_OWNER_INVENTORY_OVERLAP", "two host-owner entries claim the same byte",
                    tp_offset=byte, first=host_byte_claims[byte], second=owner_id,
                ))
            else:
                host_byte_claims[byte] = owner_id
            try:
                module_owner = owner_for_byte(tls_objects, byte)
            except VerificationError as exc:
                errors.append(exc)
                module_owner = None
            if module_owner is not None:
                errors.append(VerificationError(
                    "HOST_OWNER_MODULE_OVERLAP", "a declared host-owned byte overlaps a TLS module",
                    tp_offset=byte, module=module_owner.module_name(), host_owner=owner_id,
                ))

    aperture_cfg = config.get("main_aperture")
    aperture: Optional[dict[str, Any]] = None
    aperture_range: Optional[tuple[int, int]] = None
    main = chain[0]
    if not isinstance(aperture_cfg, dict):
        errors.append(VerificationError("APERTURE_CONFIG", "main_aperture config is required"))
    elif main.elf.tls is None or main.tls_offset is None:
        errors.append(VerificationError("MAIN_PT_TLS_MISSING", "main ELF has no PT_TLS aperture"))
    else:
        symbol_name = aperture_cfg.get("symbol")
        symbols = exact_tls_symbols(main, symbol_name) if isinstance(symbol_name, str) else []
        if len(symbols) != 1:
            errors.append(VerificationError(
                "APERTURE_SYMBOL_AMBIGUOUS" if symbols else "APERTURE_SYMBOL_MISSING",
                "main aperture TLS symbol must resolve exactly once",
                symbol=symbol_name, matches=[s.as_dict() for s in symbols],
            ))
        else:
            symbol = symbols[0]
            min_size = int(aperture_cfg.get("min_size", 0))
            if symbol.size < min_size:
                errors.append(VerificationError(
                    "APERTURE_SYMBOL_TOO_SMALL", "main aperture symbol is smaller than policy",
                    symbol=symbol.name, actual=symbol.size, minimum=min_size,
                ))
            if symbol.value + symbol.size > main.elf.tls.p_memsz:
                errors.append(VerificationError(
                    "APERTURE_SYMBOL_OUTSIDE_PT_TLS", "main aperture symbol exceeds main PT_TLS",
                    symbol=symbol.as_dict(), p_memsz=main.elf.tls.p_memsz,
                ))
            start = main.tls_offset + symbol.value
            end = start + symbol.size
            aperture_range = (start, end)
            aperture = {
                "symbol": symbol.as_dict(),
                "tp_range": [start, end - 1] if end > start else [],
                "main_pt_tls": module_tls_dict(main),
            }

    required_results: list[dict[str, Any]] = []
    for requirement in config.get("required_tls_symbols", []):
        module_name = requirement.get("module")
        symbol_name = requirement.get("symbol")
        modules = find_modules(chain, module_name) if isinstance(module_name, str) else []
        result: dict[str, Any] = {"requirement": requirement, "matches": []}
        if len(modules) != 1:
            errors.append(VerificationError(
                "REQUIRED_MODULE_AMBIGUOUS" if modules else "REQUIRED_MODULE_MISSING",
                "required TLS symbol module must resolve exactly once",
                module=module_name, matches=[str(m.elf.path) for m in modules],
            ))
        else:
            obj = modules[0]
            symbols = exact_tls_symbols(obj, symbol_name) if isinstance(symbol_name, str) else []
            result["matches"] = [s.as_dict() for s in symbols]
            if len(symbols) != 1:
                errors.append(VerificationError(
                    "REQUIRED_TLS_SYMBOL_AMBIGUOUS" if symbols else "REQUIRED_TLS_SYMBOL_MISSING",
                    "required TLS symbol must resolve exactly once",
                    module=module_name, symbol=symbol_name, matches=result["matches"],
                ))
            else:
                symbol = symbols[0]
                if "value" in requirement and symbol.value != int(requirement["value"]):
                    errors.append(VerificationError(
                        "REQUIRED_TLS_SYMBOL_VALUE", "required TLS symbol value differs",
                        module=module_name, symbol=symbol_name, actual=symbol.value,
                        expected=int(requirement["value"]),
                    ))
                if "size" in requirement and symbol.size != int(requirement["size"]):
                    errors.append(VerificationError(
                        "REQUIRED_TLS_SYMBOL_SIZE", "required TLS symbol size differs",
                        module=module_name, symbol=symbol_name, actual=symbol.size,
                        expected=int(requirement["size"]),
                    ))
                if obj.tls_offset is None:
                    errors.append(VerificationError(
                        "REQUIRED_TLS_MODULE_NOT_INITIAL", "required TLS symbol is not in initial static TLS",
                        module=module_name, symbol=symbol_name,
                    ))
                else:
                    result["tp_range"] = [
                        obj.tls_offset + symbol.value,
                        obj.tls_offset + symbol.value + max(symbol.size, 1) - 1,
                    ]
        required_results.append(result)

    slot_results: list[dict[str, Any]] = []
    for slot in config.get("slots", []):
        if not isinstance(slot, dict):
            continue
        slot_id = slot.get("id")
        try:
            offset = int(slot.get("offset", -1))
            width = int(slot.get("width", 0))
        except (TypeError, ValueError):
            continue
        result: dict[str, Any] = {
            "id": slot_id,
            "offset": offset,
            "width": width,
            "semantic": slot.get("semantic"),
            "byte_owners": [],
            "pass": True,
        }
        if width <= 0:
            errors.append(VerificationError("SLOT_RANGE", "slot offset/width is invalid", slot=slot))
            result["pass"] = False
            slot_results.append(result)
            continue
        for byte in range(offset, offset + width):
            try:
                owner = owner_for_byte(tls_objects, byte)
            except VerificationError as exc:
                errors.append(exc)
                owner = None
            host_claims = [owner_id for start, end, owner_id in host_ranges if start <= byte < end]
            in_aperture = bool(aperture_range and aperture_range[0] <= byte < aperture_range[1])
            byte_result = {
                "tp_offset": byte,
                "owner_kind": "module" if owner else ("host_reserved" if host_claims else "loader_alignment_gap"),
                "owner": owner.module_name() if owner else (host_claims[0] if len(host_claims) == 1 else host_claims or None),
                "path": str(owner.elf.path) if owner else None,
                "inside_main_aperture_symbol": in_aperture,
            }
            result["byte_owners"].append(byte_result)
            if owner is not main or not in_aperture:
                result["pass"] = False
        if not result["pass"]:
            errors.append(VerificationError(
                "SLOT_NOT_MAIN_APERTURE_OWNED",
                "every byte of an admitted Bionic inline slot must be owned by the named main-ELF aperture",
                slot=slot_id, offset=offset, width=width,
                owners=result["byte_owners"],
            ))
        slot_results.append(result)

    return aperture, required_results, slot_results


def inspect_runtime_dsos(
    paths: list[pathlib.Path], config: dict[str, Any], initial_chain: list[LoadedObject],
    loader: Optional[ElfFile], env_dirs: list[pathlib.Path], system_dirs: list[pathlib.Path],
    rootfs: Optional[pathlib.Path], cwd: pathlib.Path, errors: list[VerificationError],
) -> dict[str, Any]:
    policy = config.get("dynamic_pt_tls_policy")
    if policy != "invalidate_generation":
        errors.append(VerificationError(
            "DYNAMIC_TLS_POLICY", "dynamic PT_TLS policy must be invalidate_generation", actual=policy,
        ))
    objects: list[dict[str, Any]] = []
    closure_audit: list[dict[str, Any]] = []
    elf_policy_audit: list[dict[str, Any]] = []
    invalidators: list[str] = []
    initial_inodes = {obj.elf.file_identity for obj in initial_chain}
    for path in paths:
        try:
            elf = ElfFile(path)
        except VerificationError as exc:
            errors.append(exc)
            continue
        runtime_resolver = ClosureResolver(
            elf, loader, env_dirs, system_dirs, rootfs, cwd,
        )
        runtime_chain = runtime_resolver.resolve_initial()
        errors.extend(runtime_resolver.errors)
        elf_policy_audit.extend(audit_loaded_elf_policy(
            runtime_chain, errors, scope=f"runtime:{elf.path.name}",
        ))
        closure_audit.append({
            "root": str(elf.path),
            "resolution_audit": runtime_resolver.resolution_audit,
        })
        for obj in runtime_chain:
            item = obj.elf.identity()
            inode = obj.elf.file_identity
            item["already_in_initial_generation"] = inode in initial_inodes
            item["pt_tls"] = None
            if obj.elf.tls is not None and obj.elf.tls.p_memsz:
                item["pt_tls"] = {
                    "p_memsz": obj.elf.tls.p_memsz,
                    "p_filesz": obj.elf.tls.p_filesz,
                    "p_align": max(obj.elf.tls.p_align, 1),
                }
                if inode not in initial_inodes:
                    invalidators.append(str(obj.elf.path))
            objects.append(item)
    if invalidators:
        errors.append(VerificationError(
            "GENERATION_INVALIDATED_BY_DYNAMIC_PT_TLS",
            "runtime-loaded PT_TLS is not part of the initial proof and invalidates this generation",
            paths=sorted(set(invalidators)),
        ))
    return {
        "policy": policy,
        "objects": objects,
        "closure_resolution_audit": closure_audit,
        "elf_policy_audit": elf_policy_audit,
        "generation_invalidated": bool(invalidators),
    }


def load_config(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        config = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("CONFIG_READ_FAILED", str(exc), path=str(path)) from exc
    if config.get("schema") != "westlake-tls-ownership-v1":
        raise VerificationError("CONFIG_SCHEMA", "unsupported inventory schema", actual=config.get("schema"))
    return config, hashlib.sha256(raw).hexdigest()


def load_frozen_inputs(
    config: dict[str, Any], errors: list[VerificationError],
) -> tuple[dict[str, dict[str, Any]], dict[pathlib.Path, dict[str, Any]], list[dict[str, Any]]]:
    """Read and hash project-local product evidence without following it outside."""
    entries = config.get("frozen_inputs")
    product = config.get("product_certificate") is True
    if entries is None:
        if product:
            errors.append(VerificationError(
                "FROZEN_INPUTS_MISSING", "a product certificate requires a frozen_inputs list",
            ))
        return {}, {}, []
    if not isinstance(entries, list):
        errors.append(VerificationError("FROZEN_INPUTS_FORMAT", "frozen_inputs must be a list"))
        return {}, {}, []

    by_id: dict[str, dict[str, Any]] = {}
    by_path: dict[pathlib.Path, dict[str, Any]] = {}
    audit: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append(VerificationError("FROZEN_INPUT_FORMAT", "frozen input must be an object", entry=entry))
            continue
        artifact_id = entry.get("id")
        role = entry.get("role")
        raw_path = entry.get("project_path")
        expected_sha = entry.get("sha256")
        if not isinstance(artifact_id, str) or not artifact_id or artifact_id in by_id:
            errors.append(VerificationError(
                "FROZEN_INPUT_IDENTITY", "frozen input IDs must be unique non-empty strings", id=artifact_id,
            ))
            continue
        if not isinstance(role, str) or not role:
            errors.append(VerificationError(
                "FROZEN_INPUT_ROLE", "frozen input role must be a non-empty string", id=artifact_id, role=role,
            ))
            continue
        if not isinstance(raw_path, str) or not raw_path or pathlib.Path(raw_path).is_absolute():
            errors.append(VerificationError(
                "FROZEN_INPUT_PROJECT_PATH",
                "frozen input project_path must be project-relative",
                id=artifact_id, project_path=raw_path,
            ))
            continue
        if not is_sha256(expected_sha):
            errors.append(VerificationError(
                "FROZEN_INPUT_SHA256", "frozen input SHA-256 must be 64 lowercase hex characters",
                id=artifact_id, sha256=expected_sha,
            ))
            continue
        try:
            path = project_path(raw_path, role=f"frozen_input:{artifact_id}", regular_file=True)
        except VerificationError as exc:
            errors.append(exc)
            audit.append({
                "id": artifact_id, "role": role, "project_path": raw_path,
                "expected_sha256": expected_sha, "status": "MISSING_OR_OUTSIDE",
            })
            continue
        if path in by_path:
            errors.append(VerificationError(
                "FROZEN_INPUT_PATH_DUPLICATE",
                "one project-local file may have only one frozen artifact identity",
                first=by_path[path]["id"], second=artifact_id, path=str(path),
            ))
            continue
        actual_sha = sha256_file(path)
        item = dict(entry)
        item.update({"path": path, "actual_sha256": actual_sha})
        by_id[artifact_id] = item
        by_path[path] = item
        audit.append({
            "id": artifact_id,
            "role": role,
            "path": str(path),
            "expected_sha256": expected_sha,
            "actual_sha256": actual_sha,
            "origin_readonly_path": entry.get("origin_readonly_path"),
            "origin_sha256": entry.get("origin_sha256"),
            "status": "MATCH" if actual_sha == expected_sha else "HASH_MISMATCH",
        })
        if actual_sha != expected_sha:
            errors.append(VerificationError(
                "FROZEN_INPUT_HASH_MISMATCH", "frozen input bytes differ from the manifest",
                id=artifact_id, path=str(path), expected=expected_sha, actual=actual_sha,
            ))
        origin_path = entry.get("origin_readonly_path")
        origin_sha = entry.get("origin_sha256")
        if origin_path is not None or origin_sha is not None:
            if not isinstance(origin_path, str) or not origin_path or not is_sha256(origin_sha):
                errors.append(VerificationError(
                    "FROZEN_INPUT_ORIGIN_FORMAT",
                    "external provenance requires inert origin_readonly_path plus 64-hex origin_sha256",
                    id=artifact_id,
                ))
            elif origin_sha != expected_sha:
                errors.append(VerificationError(
                    "FROZEN_INPUT_ORIGIN_HASH_MISMATCH",
                    "recorded origin SHA must equal the copied project-local SHA",
                    id=artifact_id, origin_sha256=origin_sha, local_sha256=expected_sha,
                ))

    required_roles = config.get("required_frozen_roles", {})
    if product and not isinstance(required_roles, dict):
        errors.append(VerificationError(
            "FROZEN_ROLE_REQUIREMENTS", "product certificate requires required_frozen_roles object",
        ))
    elif isinstance(required_roles, dict):
        role_counts: dict[str, int] = {}
        for entry in by_id.values():
            role_counts[entry["role"]] = role_counts.get(entry["role"], 0) + 1
        for role, expected_count in required_roles.items():
            if not isinstance(role, str) or not isinstance(expected_count, int) or expected_count < 1:
                errors.append(VerificationError(
                    "FROZEN_ROLE_REQUIREMENTS", "role counts must be positive integers",
                    role=role, expected_count=expected_count,
                ))
                continue
            actual_count = role_counts.get(role, 0)
            if actual_count != expected_count:
                errors.append(VerificationError(
                    "FROZEN_ROLE_COUNT", "frozen role count differs from product policy",
                    role=role, expected=expected_count, actual=actual_count,
                ))
    return by_id, by_path, audit


def frozen_artifact(
    artifact_id: Any, frozen_by_id: dict[str, dict[str, Any]], errors: list[VerificationError], *, role: str,
) -> Optional[dict[str, Any]]:
    if not isinstance(artifact_id, str) or artifact_id not in frozen_by_id:
        errors.append(VerificationError(
            "FROZEN_ARTIFACT_REQUIRED", "required frozen artifact identity is missing",
            role=role, artifact_id=artifact_id,
        ))
        return None
    return frozen_by_id[artifact_id]


def validate_guest_scan(
    config: dict[str, Any], frozen_by_id: dict[str, dict[str, Any]], errors: list[VerificationError],
) -> dict[str, Any]:
    """Bind the CardWords four-DSO scan to exact APK entries and report bytes."""
    if not (
        config.get("product_certificate") is True
        or config.get("candidate_for_product_certificate") is True
    ):
        return {"required_for_product": False}
    subject = config.get("subject")
    if not isinstance(subject, dict):
        errors.append(VerificationError("PRODUCT_SUBJECT", "product subject object is required"))
        return {"required_for_product": True, "status": "MISSING"}
    apk = frozen_artifact(subject.get("apk_artifact_id"), frozen_by_id, errors, role="canonical_apk")
    native_dsos = subject.get("native_dsos")
    if not isinstance(native_dsos, list) or len(native_dsos) != 4:
        errors.append(VerificationError(
            "GUEST_DSO_SET", "CardWords product profile must bind exactly four ARM64 native DSOs",
        ))
        native_dsos = []

    expected_dsos: dict[str, dict[str, Any]] = {}
    for item in native_dsos:
        if not isinstance(item, dict):
            errors.append(VerificationError("GUEST_DSO_FORMAT", "native DSO binding must be an object", item=item))
            continue
        apk_entry = item.get("apk_entry")
        artifact = frozen_artifact(item.get("artifact_id"), frozen_by_id, errors, role="apk_native_dso")
        if not isinstance(apk_entry, str) or not apk_entry.startswith("lib/arm64-v8a/") or artifact is None:
            errors.append(VerificationError("GUEST_DSO_FORMAT", "native DSO needs ARM64 apk_entry and artifact_id", item=item))
            continue
        if artifact.get("sha256") != item.get("sha256"):
            errors.append(VerificationError(
                "GUEST_DSO_HASH_BINDING", "subject DSO SHA differs from frozen artifact",
                apk_entry=apk_entry, subject_sha256=item.get("sha256"), frozen_sha256=artifact.get("sha256"),
            ))
        basename = pathlib.PurePosixPath(apk_entry).name
        if basename in expected_dsos:
            errors.append(VerificationError("GUEST_DSO_SET", "duplicate guest DSO basename", basename=basename))
        expected_dsos[basename] = {"subject": item, "artifact": artifact}

    apk_entry_audit: list[dict[str, Any]] = []
    if apk is not None:
        try:
            with zipfile.ZipFile(apk["path"]) as archive:
                for basename, binding in expected_dsos.items():
                    entry = binding["subject"]["apk_entry"]
                    try:
                        with archive.open(entry) as stream:
                            digest = hashlib.sha256()
                            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                digest.update(chunk)
                            actual = digest.hexdigest()
                    except KeyError:
                        errors.append(VerificationError(
                            "APK_ENTRY_MISSING", "frozen APK does not contain a declared native DSO", entry=entry,
                        ))
                        continue
                    expected = binding["artifact"]["sha256"]
                    apk_entry_audit.append({"entry": entry, "sha256": actual, "frozen_sha256": expected})
                    if actual != expected:
                        errors.append(VerificationError(
                            "APK_ENTRY_HASH_MISMATCH",
                            "APK entry bytes differ from the separately frozen native DSO",
                            entry=entry, apk_sha256=actual, frozen_sha256=expected,
                        ))
        except (OSError, zipfile.BadZipFile) as exc:
            errors.append(VerificationError("APK_READ_FAILED", str(exc), path=str(apk["path"])))

    report_artifact = frozen_artifact(
        subject.get("guest_scanner_report_artifact_id"), frozen_by_id, errors, role="guest_scanner_report",
    )
    tool_artifact = frozen_artifact(
        subject.get("guest_scanner_tool_artifact_id"), frozen_by_id, errors, role="guest_scanner_tool",
    )
    audit: dict[str, Any] = {
        "required_for_product": True,
        "apk_entry_audit": apk_entry_audit,
        "scanner_tool": None if tool_artifact is None else {
            "path": str(tool_artifact["path"]), "sha256": tool_artifact["actual_sha256"],
        },
    }
    if report_artifact is None:
        audit["status"] = "REPORT_MISSING"
        return audit
    try:
        report = json.loads(report_artifact["path"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(VerificationError("GUEST_SCAN_REPORT_READ", str(exc), path=str(report_artifact["path"])))
        audit["status"] = "REPORT_INVALID"
        return audit
    audit["report"] = {"path": str(report_artifact["path"]), "sha256": report_artifact["actual_sha256"]}
    if report.get("schema") != "unity-inline-tp-scan-v1":
        errors.append(VerificationError("GUEST_SCAN_REPORT_SCHEMA", "unexpected guest scanner report schema"))
    if apk is not None and report.get("apk_sha256") != apk.get("sha256"):
        errors.append(VerificationError(
            "GUEST_SCAN_APK_MISMATCH", "scanner report APK SHA differs from frozen APK",
            report_sha256=report.get("apk_sha256"), frozen_sha256=apk.get("sha256"),
        ))
    report_dsos = report.get("dsos")
    report_map = {
        item.get("dso"): item for item in report_dsos if isinstance(item, dict) and isinstance(item.get("dso"), str)
    } if isinstance(report_dsos, list) else {}
    if set(report_map) != set(expected_dsos):
        errors.append(VerificationError(
            "GUEST_SCAN_DSO_SET_MISMATCH", "scanner report DSO set differs from four frozen APK DSOs",
            report=sorted(report_map), expected=sorted(expected_dsos),
        ))
    for name, binding in expected_dsos.items():
        if name in report_map and report_map[name].get("sha256") != binding["artifact"].get("sha256"):
            errors.append(VerificationError(
                "GUEST_SCAN_DSO_HASH_MISMATCH", "scanner report DSO hash differs from frozen bytes",
                dso=name, report_sha256=report_map[name].get("sha256"),
                frozen_sha256=binding["artifact"].get("sha256"),
            ))

    slots = [slot for slot in config.get("slots", []) if isinstance(slot, dict)]
    measured_classes: set[tuple[int, int, str, bool]] = set()
    measured_slot_ids: set[str] = set()
    for dso in report_map.values():
        classes = dso.get("classes")
        if not isinstance(classes, list):
            errors.append(VerificationError(
                "GUEST_SCAN_ACCESS_FORMAT", "guest scanner DSO lacks direct measured classes",
                dso=dso.get("dso"),
            ))
            continue
        for access in classes:
            if not isinstance(access, dict):
                continue
            try:
                offset = int(access["offset"])
                width = int(access["width"])
            except (KeyError, TypeError, ValueError):
                errors.append(VerificationError(
                    "GUEST_SCAN_ACCESS_FORMAT", "TP access class lacks integer offset/width", access=access,
                ))
                continue
            direction = str(access.get("direction"))
            atomic = bool(access.get("atomic"))
            measured_classes.add((offset, width, direction, atomic))
            owners = []
            for slot in slots:
                try:
                    slot_start = int(slot.get("offset"))
                    slot_width = int(slot.get("width"))
                except (TypeError, ValueError):
                    continue
                if slot_start <= offset and offset + width <= slot_start + slot_width:
                    owners.append(slot)
            if len(owners) != 1:
                errors.append(VerificationError(
                    "GUEST_SCAN_ACCESS_NOT_ADMITTED",
                    "every directly measured guest TP class must fit exactly one admitted semantic slot",
                    dso=dso.get("dso"), offset=offset, width=width,
                    matching_slots=[slot.get("id") for slot in owners],
                ))
                continue
            owner = owners[0]
            measured_slot_ids.add(str(owner.get("id")))
            declared_direction = owner.get("direction")
            if declared_direction is not None and declared_direction != direction:
                errors.append(VerificationError(
                    "GUEST_SCAN_ACCESS_DIRECTION",
                    "measured TP access direction differs from admitted slot policy",
                    slot=owner.get("id"), measured=direction, declared=declared_direction,
                ))

    totals = report.get("totals") if isinstance(report.get("totals"), dict) else {}
    direct_unknown = totals.get("inline_unknown_count")
    cfg_unknown = totals.get("cfg_inline_unknown_count")
    if not isinstance(direct_unknown, int) or not isinstance(cfg_unknown, int):
        errors.append(VerificationError("GUEST_SCAN_UNKNOWN_COUNTS", "scanner report lacks integer unknown counts"))
        measured_unknown: Optional[int] = None
    else:
        measured_unknown = direct_unknown + cfg_unknown
    native_scan = config.get("native_scan") if isinstance(config.get("native_scan"), dict) else {}
    expected_unknown = native_scan.get("unknown_tp_accesses")
    if measured_unknown != expected_unknown:
        errors.append(VerificationError(
            "GUEST_SCAN_UNKNOWN_MISMATCH", "inventory unknown count differs from scanner report",
            inventory=expected_unknown, report=measured_unknown,
        ))
    for field, measured in (
        ("direct_inline_unknown_count", direct_unknown),
        ("cfg_inline_unknown_count", cfg_unknown),
    ):
        if field in native_scan and native_scan.get(field) != measured:
            errors.append(VerificationError(
                "GUEST_SCAN_UNKNOWN_MISMATCH", "inventory scan counter differs from scanner report",
                field=field, inventory=native_scan.get(field), report=measured,
            ))
    observed_slot_ids = native_scan.get("observed_slot_ids")
    if not isinstance(observed_slot_ids, list) or set(observed_slot_ids) != measured_slot_ids:
        errors.append(VerificationError(
            "GUEST_SCAN_SLOT_SET_MISMATCH",
            "inventory observed slot IDs differ from slots derived from the frozen scanner report",
            inventory=observed_slot_ids, report=sorted(measured_slot_ids),
        ))
    audit.update({
        "direct_inline_unknown_count": direct_unknown,
        "cfg_inline_unknown_count": cfg_unknown,
        "unknown_tp_accesses": measured_unknown,
        "measured_access_classes": [
            {"offset": offset, "width": width, "direction": direction, "atomic": atomic}
            for offset, width, direction, atomic in sorted(measured_classes)
        ],
        "measured_slot_ids": sorted(measured_slot_ids),
        "status": "COMPLETE" if measured_unknown == 0 else "NOT_CERTIFIABLE_UNKNOWN_TP_ACCESSES",
    })
    return audit


def validate_musl_allocator_provenance(
    config: dict[str, Any], frozen_by_id: dict[str, dict[str, Any]], loader: Optional[ElfFile],
    errors: list[VerificationError],
) -> dict[str, Any]:
    if not (
        config.get("product_certificate") is True
        or config.get("candidate_for_product_certificate") is True
    ):
        return {"required_for_product": False}
    target = config.get("target") if isinstance(config.get("target"), dict) else {}
    source_status = target.get("musl_source_match")
    byte_oracle = target.get("exact_loader_allocator_oracle")
    source_proven = source_status == "PROVEN"
    byte_proven = isinstance(byte_oracle, dict) and byte_oracle.get("status") == "PROVEN"
    source_artifact = None
    byte_artifact = None
    if source_proven:
        source_artifact = frozen_artifact(
            target.get("musl_source_provenance_artifact_id"), frozen_by_id, errors,
            role="musl_source_build_provenance",
        )
        source_proven = source_artifact is not None
    if byte_proven:
        byte_artifact = frozen_artifact(
            byte_oracle.get("artifact_id"), frozen_by_id, errors, role="exact_loader_allocator_oracle",
        )
        if loader is None or byte_oracle.get("loader_sha256") != loader.sha256:
            errors.append(VerificationError(
                "MUSL_LOADER_ORACLE_IDENTITY",
                "exact-loader allocator oracle must bind the CLI loader SHA-256",
                oracle_loader_sha256=byte_oracle.get("loader_sha256"),
                actual_loader_sha256=None if loader is None else loader.sha256,
            ))
            byte_proven = False
        byte_proven = byte_proven and byte_artifact is not None
    if not source_proven and not byte_proven:
        errors.append(VerificationError(
            "MUSL_ALLOCATOR_PROVENANCE_NOT_CLOSED",
            "musl source must be build-provenance matched to the exact loader, or an independent exact-loader byte oracle must prove the allocator",
            musl_source_match=source_status,
            exact_loader_allocator_oracle=byte_oracle,
        ))
    return {
        "required_for_product": True,
        "musl_source_match": source_status,
        "source_provenance_artifact": None if source_artifact is None else source_artifact["id"],
        "exact_loader_byte_oracle_status": None if not isinstance(byte_oracle, dict) else byte_oracle.get("status"),
        "exact_loader_byte_oracle_artifact": None if byte_artifact is None else byte_artifact["id"],
        "pass": source_proven or byte_proven,
    }


def validate_initial_closure_tp_scan(
    config: dict[str, Any], frozen_by_id: dict[str, dict[str, Any]], chain: list[LoadedObject],
    loader: Optional[ElfFile], errors: list[VerificationError],
) -> dict[str, Any]:
    """Require a second scan over main+loader+recursive initial closure.

    This is intentionally independent of the CardWords guest scan.  Ownership
    alone only makes slot 5 start as zero; this gate proves that no pre-prepare
    code consumes Bionic stack-guard semantics before the explicit preparation
    point publishes the value.
    """
    if not (
        config.get("product_certificate") is True
        or config.get("candidate_for_product_certificate") is True
    ):
        return {"required_for_product": False}
    scan = config.get("initial_closure_tp_scan")
    if not isinstance(scan, dict):
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_MISSING",
            "product certificate requires a separate initial-closure TP scan",
        ))
        return {"required_for_product": True, "status": "MISSING"}
    if scan.get("complete") is not True:
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_INCOMPLETE",
            "main+loader+recursive DT_NEEDED TP scan must explicitly be complete",
        ))
    if scan.get("unknown_tp_accesses") != 0:
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_UNKNOWN",
            "unknown TP-derived accesses remain in the initial closure",
            unknown_tp_accesses=scan.get("unknown_tp_accesses"),
        ))
    if scan.get("pre_prepare_slot5_access_count") != 0:
        errors.append(VerificationError(
            "PREPARE_BEFORE_SLOT5_USE_NOT_PROVEN",
            "slot 5 is zero after reservation; no Bionic slot-5 use is allowed before explicit prepare",
            pre_prepare_slot5_access_count=scan.get("pre_prepare_slot5_access_count"),
        ))
    if scan.get("prepare_order_proven") is not True:
        errors.append(VerificationError(
            "TLS_PREPARE_ORDER_NOT_PROVEN",
            "a phase/callgraph proof must place explicit TLS prepare before every admitted slot-5 consumer",
        ))

    report_artifact = frozen_artifact(
        scan.get("report_artifact_id"), frozen_by_id, errors, role="initial_closure_tp_scan_report",
    )
    tool_artifact = frozen_artifact(
        scan.get("scanner_tool_artifact_id"), frozen_by_id, errors, role="initial_closure_tp_scanner_tool",
    )
    order_artifact = frozen_artifact(
        scan.get("prepare_order_evidence_artifact_id"), frozen_by_id, errors,
        role="tls_prepare_order_evidence",
    )
    audit: dict[str, Any] = {
        "required_for_product": True,
        "scanner_tool_artifact": None if tool_artifact is None else tool_artifact["id"],
        "prepare_order_evidence_artifact": None if order_artifact is None else order_artifact["id"],
    }
    if report_artifact is None:
        audit["status"] = "REPORT_MISSING"
        return audit
    try:
        report = json.loads(report_artifact["path"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_READ", str(exc), path=str(report_artifact["path"]),
        ))
        audit["status"] = "REPORT_INVALID"
        return audit
    if report.get("schema") != "westlake-initial-closure-tp-scan-v1":
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_SCHEMA", "unexpected initial-closure scanner report schema",
            actual=report.get("schema"),
        ))
    expected: list[tuple[str, str]] = []
    for obj in chain:
        expected.append((obj.module_name(), obj.elf.sha256))
    if loader is not None and all(obj.elf.path != loader.path for obj in chain):
        expected.append(("$MUSL_LOADER", loader.sha256))
    actual_objects = report.get("closure_objects")
    actual = sorted(
        (str(item.get("module")), str(item.get("sha256")))
        for item in actual_objects if isinstance(item, dict)
    ) if isinstance(actual_objects, list) else []
    if actual != sorted(expected):
        errors.append(VerificationError(
            "INITIAL_CLOSURE_TP_SCAN_IDENTITY_MISMATCH",
            "initial-closure TP report must bind every final main/loader/recursive DSO identity exactly",
            expected=[{"module": module, "sha256": sha} for module, sha in sorted(expected)],
            report=[{"module": module, "sha256": sha} for module, sha in actual],
        ))
    for field in (
        "complete", "unknown_tp_accesses", "pre_prepare_slot5_access_count", "prepare_order_proven",
    ):
        if report.get(field) != scan.get(field):
            errors.append(VerificationError(
                "INITIAL_CLOSURE_TP_SCAN_FIELD_MISMATCH",
                "inventory field differs from frozen initial-closure TP report",
                field=field, inventory=scan.get(field), report=report.get(field),
            ))
    audit.update({
        "report_path": str(report_artifact["path"]),
        "report_sha256": report_artifact["actual_sha256"],
        "closure_object_count": len(actual),
        "status": "COMPLETE" if (
            report.get("complete") is True
            and report.get("unknown_tp_accesses") == 0
            and report.get("pre_prepare_slot5_access_count") == 0
            and report.get("prepare_order_proven") is True
            and actual == sorted(expected)
        ) else "NOT_CERTIFIABLE",
    })
    return audit


def validate_product_bindings(
    config: dict[str, Any], frozen_by_id: dict[str, dict[str, Any]],
    frozen_by_path: dict[pathlib.Path, dict[str, Any]], main: ElfFile, loader: Optional[ElfFile],
    chain: list[LoadedObject], sidecar_audit: list[dict[str, Any]], runtime: dict[str, Any],
    runtime_roots: list[pathlib.Path], errors: list[VerificationError],
) -> dict[str, Any]:
    if config.get("product_certificate") is not True:
        return {"required_for_product": False}
    bindings = config.get("product_bindings")
    if not isinstance(bindings, dict):
        errors.append(VerificationError("PRODUCT_BINDINGS_MISSING", "product_bindings object is required"))
        return {"required_for_product": True, "status": "MISSING"}

    def match_elf(artifact_id: Any, elf: Optional[ElfFile], role: str) -> Optional[dict[str, Any]]:
        artifact = frozen_artifact(artifact_id, frozen_by_id, errors, role=role)
        if artifact is None or elf is None:
            if elf is None:
                errors.append(VerificationError("PRODUCT_ELF_MISSING", "required product ELF was not supplied", role=role))
            return artifact
        if artifact["path"] != elf.path or artifact["actual_sha256"] != elf.sha256:
            errors.append(VerificationError(
                "PRODUCT_ELF_BINDING_MISMATCH", "CLI ELF differs from its frozen product binding",
                role=role, artifact_id=artifact_id, frozen_path=str(artifact["path"]),
                actual_path=str(elf.path), frozen_sha256=artifact["actual_sha256"], actual_sha256=elf.sha256,
            ))
        return artifact

    main_artifact = match_elf(bindings.get("main_elf_artifact_id"), main, "main_elf_stripped")
    loader_artifact = match_elf(bindings.get("loader_artifact_id"), loader, "musl_loader")

    sidecar_map = bindings.get("symbol_sidecars")
    if not isinstance(sidecar_map, dict):
        errors.append(VerificationError(
            "PRODUCT_SIDECAR_BINDINGS", "product must bind main and libselinux symbol sidecars",
        ))
        sidecar_map = {}
    sidecars_by_module = {item.get("module"): item for item in sidecar_audit}
    for module, artifact_id in sidecar_map.items():
        artifact = frozen_artifact(artifact_id, frozen_by_id, errors, role=f"symbol_sidecar:{module}")
        actual = sidecars_by_module.get(module)
        if artifact is None or actual is None:
            if actual is None:
                errors.append(VerificationError(
                    "PRODUCT_SIDECAR_MISSING", "bound product sidecar was not supplied", module=module,
                ))
            continue
        if str(artifact["path"]) != actual.get("sidecar_path") or artifact["actual_sha256"] != actual.get("sidecar_sha256"):
            errors.append(VerificationError(
                "PRODUCT_SIDECAR_BINDING_MISMATCH", "CLI sidecar differs from frozen binding",
                module=module, artifact_id=artifact_id, actual=actual,
            ))

    required_modules = bindings.get("required_initial_modules")
    if not isinstance(required_modules, list):
        errors.append(VerificationError(
            "PRODUCT_REQUIRED_MODULES", "required_initial_modules must bind libbeget and libselinux",
        ))
        required_modules = []
    required_names: set[str] = set()
    for item in required_modules:
        if not isinstance(item, dict) or not isinstance(item.get("module"), str):
            errors.append(VerificationError("PRODUCT_REQUIRED_MODULES", "invalid required module binding", item=item))
            continue
        module = item["module"]
        required_names.add(module)
        artifact = frozen_artifact(item.get("artifact_id"), frozen_by_id, errors, role=f"initial_module:{module}")
        matches = find_modules(chain, module)
        if len(matches) != 1:
            errors.append(VerificationError(
                "PRODUCT_REQUIRED_MODULE_IDENTITY", "required initial module must resolve exactly once",
                module=module, matches=[str(obj.elf.path) for obj in matches],
            ))
            continue
        obj = matches[0]
        if artifact is not None and (
            artifact["path"] != obj.elf.path or artifact["actual_sha256"] != obj.elf.sha256
        ):
            errors.append(VerificationError(
                "PRODUCT_REQUIRED_MODULE_BINDING_MISMATCH",
                "required initial module differs from frozen artifact",
                module=module, actual_path=str(obj.elf.path), actual_sha256=obj.elf.sha256,
                frozen_path=str(artifact["path"]), frozen_sha256=artifact["actual_sha256"],
            ))
        if item.get("must_have_pt_tls") is True and (obj.elf.tls is None or obj.elf.tls.p_memsz == 0):
            errors.append(VerificationError(
                "PRODUCT_REQUIRED_MODULE_PT_TLS", "required module unexpectedly has no non-empty PT_TLS",
                module=module,
            ))
    for mandatory in ("libbegetutil.z.so", "libselinux.z.so"):
        if mandatory not in required_names:
            errors.append(VerificationError(
                "PRODUCT_REQUIRED_MODULES", "mandatory TLS layout module is not bound", module=mandatory,
            ))

    initial_unmanifested: list[dict[str, str]] = []
    if bindings.get("require_entire_initial_closure_manifested") is not True:
        errors.append(VerificationError(
            "INITIAL_CLOSURE_MANIFEST_POLICY",
            "product must require every initial closure object to be frozen",
        ))
    else:
        for obj in chain:
            artifact = frozen_by_path.get(obj.elf.path)
            if artifact is None or artifact["actual_sha256"] != obj.elf.sha256:
                initial_unmanifested.append({"path": str(obj.elf.path), "sha256": obj.elf.sha256})
        if loader is not None and loader.path not in {obj.elf.path for obj in chain}:
            artifact = frozen_by_path.get(loader.path)
            if artifact is None or artifact["actual_sha256"] != loader.sha256:
                initial_unmanifested.append({"path": str(loader.path), "sha256": loader.sha256})
        if initial_unmanifested:
            errors.append(VerificationError(
                "INITIAL_CLOSURE_NOT_FULLY_FROZEN",
                "every main/loader/recursive DT_NEEDED object must have a project-local frozen identity",
                objects=initial_unmanifested,
            ))

    expected_runtime_ids = bindings.get("runtime_root_artifact_ids")
    expected_runtime_paths: set[pathlib.Path] = set()
    if not isinstance(expected_runtime_ids, list) or len(expected_runtime_ids) != 4:
        errors.append(VerificationError(
            "RUNTIME_ROOT_BINDINGS", "CardWords product must bind exactly four runtime DSO roots",
        ))
        expected_runtime_ids = []
    for artifact_id in expected_runtime_ids:
        artifact = frozen_artifact(artifact_id, frozen_by_id, errors, role="runtime_dso_root")
        if artifact is not None:
            expected_runtime_paths.add(artifact["path"])
    actual_runtime_paths = {path.resolve() for path in runtime_roots}
    if expected_runtime_paths != actual_runtime_paths:
        errors.append(VerificationError(
            "RUNTIME_ROOT_BINDING_MISMATCH", "--runtime-dso roots differ from four frozen CardWords DSOs",
            expected=sorted(str(path) for path in expected_runtime_paths),
            actual=sorted(str(path) for path in actual_runtime_paths),
        ))

    runtime_unmanifested: list[dict[str, str]] = []
    if bindings.get("require_entire_runtime_closure_manifested") is not True:
        errors.append(VerificationError(
            "RUNTIME_CLOSURE_MANIFEST_POLICY",
            "product must require every declared runtime root closure object to be frozen",
        ))
    else:
        for item in runtime.get("objects", []):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            path = pathlib.Path(item["path"])
            artifact = frozen_by_path.get(path)
            if artifact is None or artifact["actual_sha256"] != item.get("sha256"):
                runtime_unmanifested.append({"path": str(path), "sha256": str(item.get("sha256"))})
        if runtime_unmanifested:
            errors.append(VerificationError(
                "RUNTIME_CLOSURE_NOT_FULLY_FROZEN",
                "every declared runtime root and recursive dependency must have a frozen identity",
                objects=runtime_unmanifested,
            ))

    return {
        "required_for_product": True,
        "main_artifact": None if main_artifact is None else main_artifact["id"],
        "loader_artifact": None if loader_artifact is None else loader_artifact["id"],
        "initial_closure_unmanifested": initial_unmanifested,
        "runtime_closure_unmanifested": runtime_unmanifested,
        "status": "BOUND" if not initial_unmanifested and not runtime_unmanifested else "INCOMPLETE",
    }


def verify(args: argparse.Namespace) -> dict[str, Any]:
    errors: list[VerificationError] = []
    args.inventory = project_path(args.inventory, role="inventory", regular_file=True)
    args.exe = project_path(args.exe, role="main_elf", regular_file=True)
    if args.loader is not None:
        args.loader = project_path(args.loader, role="musl_loader", regular_file=True)
    args.env_dir = [
        project_path(path, role="env_search_dir", directory=True) for path in args.env_dir
    ]
    args.system_dir = [
        project_path(path, role="initial_system_dir", directory=True) for path in args.system_dir
    ]
    args.runtime_system_dir = [
        project_path(path, role="runtime_system_dir", directory=True) for path in args.runtime_system_dir
    ]
    if args.rootfs is not None:
        args.rootfs = project_path(args.rootfs, role="rootfs", directory=True)
    args.cwd = project_path(args.cwd, role="target_cwd", directory=True)
    args.runtime_dso = [
        project_path(path, role="runtime_dso", regular_file=True) for path in args.runtime_dso
    ]
    config, inventory_sha256 = load_config(args.inventory)
    target = config.get("target", {})
    if args.require_product_certificate and config.get("product_certificate") is not True:
        errors.append(VerificationError(
            "PRODUCT_CERTIFICATE_REQUIRED",
            "this invocation requires product_certificate=true and all product evidence gates",
        ))
    frozen_by_id, frozen_by_path, frozen_audit = load_frozen_inputs(config, errors)
    guest_scan_audit = validate_guest_scan(config, frozen_by_id, errors)
    if config.get("inventory_complete") is not True:
        errors.append(VerificationError(
            "INVENTORY_NOT_COMPLETE",
            "slot inventory must explicitly assert inventory_complete=true after native-code scanning",
        ))
    native_scan = config.get("native_scan")
    if not isinstance(native_scan, dict) or native_scan.get("complete") is not True:
        errors.append(VerificationError(
            "NATIVE_SCAN_INCOMPLETE", "CardWords guest TP-relative access scan must explicitly be complete",
        ))
    if isinstance(native_scan, dict) and native_scan.get("unknown_tp_accesses") != 0:
        errors.append(VerificationError(
            "NATIVE_SCAN_UNKNOWN_TP_ACCESS",
            "unknown guest TP-derived accesses prevent a complete inline-slot inventory",
            unknown_tp_accesses=native_scan.get("unknown_tp_accesses"),
        ))
    slots = config.get("slots")
    if not isinstance(slots, list) or not slots:
        errors.append(VerificationError("SLOT_INVENTORY_EMPTY", "at least one admitted inline TLS slot is required"))
    else:
        slot_ids = [slot.get("id") for slot in slots if isinstance(slot, dict)]
        if len(slot_ids) != len(set(slot_ids)) or any(not isinstance(slot_id, str) or not slot_id for slot_id in slot_ids):
            errors.append(VerificationError("SLOT_IDENTITY", "slot IDs must be non-empty and unique"))
        observed_ids = native_scan.get("observed_slot_ids") if isinstance(native_scan, dict) else None
        if not isinstance(observed_ids, list) or set(observed_ids) != set(slot_ids):
            errors.append(VerificationError(
                "NATIVE_SCAN_SLOT_SET_MISMATCH",
                "inventory slots must exactly equal the complete native scan's observed slot IDs",
                inventory_slot_ids=slot_ids, observed_slot_ids=observed_ids,
            ))
        claimed_bytes: dict[int, str] = {}
        for slot in slots:
            if not isinstance(slot, dict):
                errors.append(VerificationError("SLOT_FORMAT", "every slot entry must be an object", slot=slot))
                continue
            try:
                start = int(slot.get("offset", -1))
                width = int(slot.get("width", 0))
            except (TypeError, ValueError):
                errors.append(VerificationError("SLOT_RANGE", "slot offset/width must be integers", slot=slot))
                continue
            if width <= 0:
                continue
            for byte in range(start, start + width):
                prior = claimed_bytes.get(byte)
                if prior is not None:
                    errors.append(VerificationError(
                        "SLOT_INVENTORY_OVERLAP", "two inventory entries claim the same TP-relative byte",
                        tp_offset=byte, first=prior, second=slot.get("id"),
                    ))
                else:
                    claimed_bytes[byte] = str(slot.get("id"))
    host_owners = config.get("host_tp_owners")
    if config.get("host_owner_inventory_complete") is not True or not isinstance(host_owners, list):
        errors.append(VerificationError(
            "HOST_OWNER_INVENTORY_INCOMPLETE",
            "target generation must explicitly bind a complete TP-relative host-owner inventory",
        ))
    else:
        for owner in host_owners:
            if not isinstance(owner, dict) or not isinstance(owner.get("id"), str):
                errors.append(VerificationError("HOST_OWNER_FORMAT", "invalid host-owner entry", owner=owner))
                continue
            try:
                int(owner.get("offset"))
                width = int(owner.get("width"))
            except (TypeError, ValueError):
                errors.append(VerificationError("HOST_OWNER_FORMAT", "host-owner offset/width must be integers", owner=owner))
                continue
            if width <= 0:
                errors.append(VerificationError("HOST_OWNER_FORMAT", "host-owner width must be positive", owner=owner))
    initial_preloads = config.get("initial_preloads")
    if not isinstance(initial_preloads, list):
        errors.append(VerificationError(
            "PRELOAD_MANIFEST_MISSING", "inventory must bind an explicit initial_preloads list",
        ))
    elif config.get("forbid_preload", True) and initial_preloads:
        errors.append(VerificationError(
            "PRELOAD_FORBIDDEN", "inventory forbids initial preload objects", preloads=initial_preloads,
        ))
    if target.get("tls_model") != "TLS_ABOVE_TP":
        errors.append(VerificationError("TLS_MODEL", "only OH musl TLS_ABOVE_TP is modeled"))
    gap = int(target.get("gap_above_tp", -1))
    if gap < 0:
        errors.append(VerificationError("TLS_GAP", "gap_above_tp must be non-negative", actual=gap))
        gap = 0
    if config.get("forbid_env_search", True) and args.env_dir:
        errors.append(VerificationError(
            "ENV_SEARCH_FORBIDDEN", "inventory forbids LD_LIBRARY_PATH/env search directories",
            env_dirs=[str(p) for p in args.env_dir],
        ))

    main = ElfFile(args.exe)
    loader = ElfFile(args.loader) if args.loader else None
    expected_machine = int(target.get("machine", EM_AARCH64))
    for role, elf in [("main", main), ("loader", loader)]:
        if elf is not None and elf.e_machine != expected_machine:
            errors.append(VerificationError(
                "ELF_MACHINE", "ELF machine differs from inventory target",
                role=role, path=str(elf.path), actual=elf.e_machine, expected=expected_machine,
            ))
    if target.get("require_pie", True) and main.e_type != ET_DYN:
        errors.append(VerificationError(
            "MAIN_NOT_PIE", "main ELF must be ET_DYN/PIE", path=str(main.path), elf_type=main.e_type,
        ))

    resolver = ClosureResolver(
        main, loader, args.env_dir, args.system_dir, args.rootfs, args.cwd,
    )
    chain = resolver.resolve_initial()
    errors.extend(resolver.errors)
    for obj in chain:
        if obj.elf.e_machine != expected_machine:
            errors.append(VerificationError(
                "ELF_MACHINE", "closure object machine differs from inventory target",
                path=str(obj.elf.path), actual=obj.elf.e_machine, expected=expected_machine,
            ))

    policy_objects = list(chain)
    if loader is not None and all(obj.elf.path != loader.path for obj in chain):
        policy_objects.append(LoadedObject(
            loader, str(loader.path), None, "libc.so", is_loader=True,
        ))
    initial_elf_policy_audit = audit_loaded_elf_policy(
        policy_objects, errors, scope="initial",
    )
    musl_allocator_audit = validate_musl_allocator_provenance(
        config, frozen_by_id, loader, errors,
    )

    closure_name_audit = audit_closure_name_collisions(chain, errors)
    sidecar_audit = attach_symbol_sidecars(
        chain, args.symbol_sidecar, expected_machine, errors,
    )

    tls_objects, tls_end = compute_initial_tls_layout(chain, gap, errors)
    try:
        owner_ranges = compressed_owner_ranges(tls_objects, tls_end)
    except VerificationError as exc:
        errors.append(exc)
        owner_ranges = []
    aperture, required_symbols, slot_results = evaluate_inventory(
        config, chain, tls_objects, errors,
    )
    runtime = inspect_runtime_dsos(
        args.runtime_dso, config, chain, loader, args.env_dir,
        args.runtime_system_dir or args.system_dir,
        args.rootfs, args.cwd, errors,
    )
    initial_closure_scan_audit = validate_initial_closure_tp_scan(
        config, frozen_by_id, chain, loader, errors,
    )
    product_binding_audit = validate_product_bindings(
        config, frozen_by_id, frozen_by_path, main, loader, chain,
        sidecar_audit, runtime, args.runtime_dso, errors,
    )

    load_order: list[dict[str, Any]] = []
    for index, obj in enumerate(chain):
        item = obj.elf.identity()
        item.update({
            "load_index": index,
            "module": obj.module_name(),
            "requested_as": obj.requested_as,
            "needed_by": obj.needed_by,
            "is_main": obj.is_main,
            "is_musl_loader": obj.is_loader,
            "pt_tls": module_tls_dict(obj),
        })
        load_order.append(item)

    return {
        "schema": "westlake-tls-ownership-report-v1",
        "verdict": "PASS" if not errors else "FAIL",
        "proof_scope": {
            "initial_dt_needed_closure_only": True,
            "tls_model": "OH_musl_AArch64_TLS_ABOVE_TP",
            "gap_above_tp": gap,
            "runtime_dlopen_folded_into_initial_closure": False,
            "product_certificate_requested": bool(args.require_product_certificate),
            "product_certificate_profile": config.get("product_certificate") is True,
        },
        "input": {
            "main": str(main.path),
            "loader": str(loader.path) if loader else None,
            "inventory": str(args.inventory.resolve()),
            "inventory_sha256": inventory_sha256,
            "verifier_sha256": sha256_file(pathlib.Path(__file__).resolve()),
            "env_dirs": [str(p.resolve()) for p in args.env_dir],
            "system_dirs": [str(p.resolve()) for p in args.system_dir],
            "runtime_system_dirs": [str(p.resolve()) for p in args.runtime_system_dir],
            "rootfs": str(args.rootfs.resolve()) if args.rootfs else None,
            "cwd": str(args.cwd.resolve()),
        },
        "load_order": load_order,
        "resolution_audit": resolver.resolution_audit,
        "closure_name_audit": closure_name_audit,
        "initial_elf_policy_audit": initial_elf_policy_audit,
        "symbol_sidecar_audit": sidecar_audit,
        "frozen_input_audit": frozen_audit,
        "guest_scan_audit": guest_scan_audit,
        "musl_allocator_provenance_audit": musl_allocator_audit,
        "initial_closure_tp_scan_audit": initial_closure_scan_audit,
        "product_binding_audit": product_binding_audit,
        "initial_tls": {
            "end_offset_exclusive": tls_end,
            "byte_owner_ranges": owner_ranges,
            "main_aperture": aperture,
            "required_tls_symbols": required_symbols,
            "slot_results": slot_results,
        },
        "runtime_load_assessment": runtime,
        "errors": [error.as_dict() for error in errors],
    }


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=pathlib.Path, required=True, help="final appspawn-x ELF")
    parser.add_argument("--inventory", type=pathlib.Path, required=True, help="slot inventory JSON")
    parser.add_argument("--loader", type=pathlib.Path, help="exact ld-musl-aarch64.so.1; required if libc is needed")
    parser.add_argument("--env-dir", type=pathlib.Path, action="append", default=[], help="sealed LD_LIBRARY_PATH directory")
    parser.add_argument("--system-dir", type=pathlib.Path, action="append", default=[], help="sealed musl system search directory")
    parser.add_argument(
        "--runtime-system-dir", type=pathlib.Path, action="append", default=[],
        help="sealed runtime/ClassLoader search directory; defaults to --system-dir",
    )
    parser.add_argument("--rootfs", type=pathlib.Path, help="map absolute target paths beneath this extracted root")
    parser.add_argument("--cwd", type=pathlib.Path, default=pathlib.Path.cwd(), help="target cwd for relative explicit paths")
    parser.add_argument(
        "--runtime-dso", type=pathlib.Path, action="append", default=[],
        help="inspect, but never append, a prospective runtime-loaded DSO",
    )
    parser.add_argument(
        "--symbol-sidecar", action="append", default=[], metavar="MODULE=PATH",
        help="same-Build-ID unstripped symbol evidence for a stripped final module",
    )
    parser.add_argument(
        "--require-product-certificate", action="store_true",
        help="reject fixture/scanner-only inventories and require every product evidence gate",
    )
    parser.add_argument("--report", type=pathlib.Path, help="write canonical JSON report here")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    report_path: Optional[pathlib.Path] = None
    try:
        if args.report:
            report_path = project_path(args.report, role="report_output", must_exist=False)
            project_path(report_path.parent, role="report_output_parent", directory=True)
        report = verify(args)
    except VerificationError as exc:
        report = {
            "schema": "westlake-tls-ownership-report-v1",
            "verdict": "FAIL",
            "errors": [exc.as_dict()],
        }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if report_path is not None:
        report_path.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if report.get("verdict") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
