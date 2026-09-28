#!/usr/bin/env python3
"""Fail-closed ELF gate for the product thread-template publisher fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import struct
from dataclasses import dataclass


PT_LOAD = 1
PT_INTERP = 3
PT_TLS = 7
PT_GNU_RELRO = 0x6474E552
PF_R = 4
PF_W = 2
PF_X = 1
SHT_SYMTAB = 2
STT_FUNC = 2
STT_OBJECT = 1
STT_TLS = 6
EM_AARCH64 = 183
ET_DYN = 3


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class ProgramHeader:
    kind: int
    flags: int
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    align: int


@dataclass(frozen=True)
class Section:
    kind: int
    offset: int
    size: int
    link: int
    entsize: int


@dataclass(frozen=True)
class Symbol:
    name: str
    info: int
    value: int
    size: int

    @property
    def kind(self) -> int:
        return self.info & 0x0F


class Elf64:
    def __init__(self, path: pathlib.Path):
        self.path = path
        self.data = path.read_bytes()
        if len(self.data) < 64 or self.data[:6] != b"\x7fELF\x02\x01":
            raise ValueError(f"not ELF64 little-endian: {path}")
        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        self.elf_type = header[1]
        self.machine = header[2]
        self.phoff = header[5]
        self.shoff = header[6]
        self.phentsize = header[9]
        self.phnum = header[10]
        self.shentsize = header[11]
        self.shnum = header[12]
        self.shstrndx = header[13]
        if self.phentsize != 56 or self.shentsize != 64:
            raise ValueError("unexpected ELF64 entry size")
        self.program_headers = self._program_headers()
        self.sections = self._sections()
        self.symbols = self._symbols()

    def _program_headers(self) -> list[ProgramHeader]:
        result = []
        for index in range(self.phnum):
            fields = struct.unpack_from(
                "<IIQQQQQQ", self.data, self.phoff + index * self.phentsize)
            result.append(ProgramHeader(
                kind=fields[0], flags=fields[1], offset=fields[2],
                vaddr=fields[3], filesz=fields[5], memsz=fields[6],
                align=fields[7]))
        return result

    def _sections(self) -> list[Section]:
        raw = [struct.unpack_from(
            "<IIQQQQIIQQ", self.data, self.shoff + i * self.shentsize)
            for i in range(self.shnum)]
        return [Section(kind=item[1], offset=item[4], size=item[5],
                        link=item[6], entsize=item[9]) for item in raw]

    def _symbols(self) -> list[Symbol]:
        result = []
        for section in self.sections:
            if section.kind != SHT_SYMTAB or section.entsize != 24:
                continue
            if section.link >= len(self.sections):
                raise ValueError("invalid symbol string table")
            strings_section = self.sections[section.link]
            strings = self.data[
                strings_section.offset:strings_section.offset +
                strings_section.size]
            for index in range(section.size // section.entsize):
                fields = struct.unpack_from(
                    "<IBBHQQ", self.data,
                    section.offset + index * section.entsize)
                name_offset = fields[0]
                if name_offset >= len(strings):
                    name = ""
                else:
                    end = strings.find(b"\0", name_offset)
                    if end < 0:
                        end = len(strings)
                    name = strings[name_offset:end].decode(
                        "utf-8", "replace")
                result.append(Symbol(name=name, info=fields[1],
                                     value=fields[4], size=fields[5]))
        return result

    def one_segment(self, kind: int) -> ProgramHeader | None:
        matches = [item for item in self.program_headers
                   if item.kind == kind]
        return matches[0] if len(matches) == 1 else None

    def one_symbol(self, name: str) -> Symbol | None:
        matches = [item for item in self.symbols if item.name == name]
        return matches[0] if len(matches) == 1 else None

    def bytes_at_vaddr(self, address: int, size: int) -> bytes:
        for segment in self.program_headers:
            if segment.kind != PT_LOAD:
                continue
            if (segment.vaddr <= address and
                    address + size <= segment.vaddr + segment.filesz):
                offset = segment.offset + address - segment.vaddr
                return self.data[offset:offset + size]
        raise ValueError(f"address is not file-backed: 0x{address:x}+{size}")


def contains(outer_begin: int, outer_end: int,
             inner_begin: int, inner_end: int) -> bool:
    return outer_begin <= inner_begin < inner_end <= outer_end


def parse_contract(elf: Elf64, symbol: Symbol) -> dict[str, int]:
    raw = elf.bytes_at_vaddr(symbol.value, symbol.size)
    if len(raw) != 24:
        raise ValueError(f"unexpected publisher contract size: {len(raw)}")
    fields = struct.unpack("<IHHHH12B", raw)
    return {
        "magic": fields[0], "version": fields[1],
        "reservation_size": fields[2], "publish_offset": fields[3],
        "guard_size": fields[4], "main_image_locator": fields[5],
        "template_patch": fields[6], "restore_protection": fields[7],
        "requires_relro": fields[8], "publisher_count": fields[9],
        "explicit_epoch_mode": fields[10],
        "fork_child_reset": fields[11],
        "clear_inherited_template": fields[12],
        "same_adapter_generation": fields[13],
        "full_image_compare": fields[14],
        "reserved_zero_0": fields[15],
        "reserved_zero_1": fields[16],
    }


def inspect(path: pathlib.Path) -> dict:
    elf = Elf64(path)
    errors: list[str] = []
    if elf.machine != EM_AARCH64:
        errors.append("NOT_AARCH64")
    if elf.elf_type != ET_DYN:
        errors.append("NOT_PIE_ET_DYN")

    interpreter = elf.one_segment(PT_INTERP)
    interpreter_value = None
    if interpreter is None:
        errors.append("INTERPRETER_COUNT_NOT_ONE")
    else:
        interpreter_value = elf.data[
            interpreter.offset:interpreter.offset + interpreter.filesz
        ].rstrip(b"\0").decode("utf-8", "replace")
        if interpreter_value != "/lib/ld-musl-aarch64.so.1":
            errors.append("INTERPRETER_IDENTITY_INVALID")

    tls = elf.one_segment(PT_TLS)
    if tls is None:
        errors.append("PT_TLS_COUNT_NOT_ONE")
        template = b""
    else:
        if (tls.filesz, tls.memsz, tls.align, tls.flags) != (48, 48, 16, PF_R):
            errors.append("PT_TLS_SHAPE_NOT_48_48_16_R")
        template = elf.data[tls.offset:tls.offset + tls.filesz]
        if (len(template) != 48 or template[0] != 0x51 or
                template[47] != 0xA7 or template[24:32] != b"\0" * 8):
            errors.append("TLS_TEMPLATE_BYTES_INVALID")
        tls_begin = tls.vaddr
        tls_end = tls_begin + tls.filesz
        loads = [item for item in elf.program_headers
                 if item.kind == PT_LOAD and
                 contains(item.vaddr, item.vaddr + item.filesz,
                          tls_begin, tls_end)]
        if (len(loads) != 1 or
                loads[0].flags & (PF_R | PF_W | PF_X) != (PF_R | PF_W)):
            errors.append("TLS_NOT_IN_RW_FILE_LOAD")
        relro = elf.one_segment(PT_GNU_RELRO)
        if relro is None:
            errors.append("GNU_RELRO_COUNT_NOT_ONE")
        else:
            page_begin = tls_begin & -4096
            page_end = (tls_end + 4095) & -4096
            relro_begin = relro.vaddr & -4096
            relro_end = (relro.vaddr + relro.memsz + 4095) & -4096
            if not contains(relro_begin, relro_end, page_begin, page_end):
                errors.append("TLS_TEMPLATE_PAGE_NOT_RELRO_COVERED")

    reservation = elf.one_symbol(
        "westlake_bionic_tls_slots_2_7_reservation")
    slot = elf.one_symbol("westlake_bionic_stack_guard_template_slot")
    if (reservation is None or reservation.kind != STT_TLS or
            reservation.size != 48 or reservation.value != 0):
        errors.append("RESERVATION_TLS_SYMBOL_INVALID")
    if slot is None or slot.kind != STT_TLS or slot.size != 8:
        errors.append("SLOT_TLS_SYMBOL_INVALID")
    if reservation is not None and slot is not None and \
            slot.value - reservation.value != 24:
        errors.append("SLOT_RELATIVE_OFFSET_NOT_24")

    publisher = elf.one_symbol("WLTP_PublishMainThreadTemplate")
    if publisher is None or publisher.kind != STT_FUNC or publisher.size == 0:
        errors.append("PRODUCT_PUBLISHER_FUNCTION_MISSING")
    publish_state = elf.one_symbol("g_publish_state")
    if (publish_state is None or publish_state.kind != STT_OBJECT or \
            publish_state.size != 4):
        errors.append("PROCESS_EXACT_ONCE_STATE_NOT_NON_TLS_OBJECT")
    if any(name.startswith(("__emutls_v.", "__emutls_t."))
           for name in (symbol.name for symbol in elf.symbols)):
        errors.append("EMULATED_TLS_SURVIVED")

    contract_symbol = elf.one_symbol("wltp_publisher_contract_v1")
    if contract_symbol is None:
        errors.append("CONTRACT_SYMBOL_MISSING")
        contract: dict[str, int] = {}
    else:
        contract = parse_contract(elf, contract_symbol)
        if contract.get("magic") != 0x574C5450 or \
                contract.get("version") != 1:
            errors.append("CONTRACT_IDENTITY_INVALID")
        if contract.get("reservation_size") != 48 or \
                contract.get("guard_size") != 8:
            errors.append("CONTRACT_SIZE_INVALID")
        if contract.get("publish_offset") != 24:
            errors.append("PUBLISH_OFFSET_NOT_24")
        if contract.get("main_image_locator") != 1:
            errors.append("MAIN_IMAGE_LOCATOR_NOT_USED")
        if contract.get("template_patch") != 1:
            errors.append("TEMPLATE_PATCH_DISABLED")
        if contract.get("restore_protection") != 1:
            errors.append("RESTORE_DISABLED")
        if contract.get("requires_relro") != 1:
            errors.append("RELRO_NOT_REQUIRED")
        if contract.get("publisher_count") != 1:
            errors.append("PUBLISHER_COUNT_NOT_ONE")
        if contract.get("explicit_epoch_mode") != 1:
            errors.append("EXPLICIT_EPOCH_MODE_DISABLED")
        if contract.get("fork_child_reset") != 1:
            errors.append("FORK_CHILD_RESET_DISABLED")
        if contract.get("clear_inherited_template") != 1:
            errors.append("INHERITED_TEMPLATE_CLEAR_DISABLED")
        if contract.get("same_adapter_generation") != 1:
            errors.append("SAME_ADAPTER_GENERATION_DISABLED")
        if contract.get("full_image_compare") != 1:
            errors.append("FULL_IMAGE_COMPARE_DISABLED")
        if contract.get("reserved_zero_0") != 0 or \
                contract.get("reserved_zero_1") != 0:
            errors.append("CONTRACT_RESERVED_NONZERO")

    return {
        "path": str(path), "sha256": sha256(path),
        "interpreter": interpreter_value,
        "pt_tls": None if tls is None else {
            "filesz": tls.filesz, "memsz": tls.memsz,
            "align": tls.align, "flags": tls.flags,
        },
        "template_hex": template.hex(), "contract": contract,
        "errors": sorted(set(errors)),
    }


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def make_rwx_load_mutant(source: pathlib.Path,
                         destination: pathlib.Path) -> None:
    data = bytearray(source.read_bytes())
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data, 0)
    phoff, phentsize, phnum = header[5], header[9], header[10]
    tls_begin = tls_end = None
    for index in range(phnum):
        offset = phoff + index * phentsize
        fields = struct.unpack_from("<IIQQQQQQ", data, offset)
        if fields[0] == PT_TLS:
            tls_begin, tls_end = fields[3], fields[3] + fields[5]
            break
    require(tls_begin is not None and tls_end is not None,
            "valid fixture has no PT_TLS for RWX mutant")
    mutated = False
    for index in range(phnum):
        offset = phoff + index * phentsize
        fields = struct.unpack_from("<IIQQQQQQ", data, offset)
        if (fields[0] == PT_LOAD and
                contains(fields[3], fields[3] + fields[5],
                         tls_begin, tls_end)):
            struct.pack_into("<I", data, offset + 4, fields[1] | PF_X)
            mutated = True
            break
    require(mutated, "could not create RWX containing-LOAD mutant")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--valid", type=pathlib.Path, required=True)
    parser.add_argument("--second-valid", type=pathlib.Path, required=True)
    parser.add_argument("--unpatched", type=pathlib.Path, required=True)
    parser.add_argument("--wrong-offset", type=pathlib.Path, required=True)
    parser.add_argument("--wrong-image", type=pathlib.Path, required=True)
    parser.add_argument("--protection-not-restored", type=pathlib.Path,
                        required=True)
    parser.add_argument("--conflict", type=pathlib.Path, required=True)
    parser.add_argument("--no-exact-once", type=pathlib.Path, required=True)
    parser.add_argument("--skip-child-reset", type=pathlib.Path,
                        required=True)
    parser.add_argument("--reuse-parent-template", type=pathlib.Path,
                        required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()

    rwx_path = args.output.parent / "mutants/rwx-load/thread-template-target"
    make_rwx_load_mutant(args.valid, rwx_path)

    valid = inspect(args.valid)
    second = inspect(args.second_valid)
    mutants = {
        "unpatched": inspect(args.unpatched),
        "wrong_offset": inspect(args.wrong_offset),
        "wrong_image": inspect(args.wrong_image),
        "protection_not_restored": inspect(args.protection_not_restored),
        "conflict": inspect(args.conflict),
        "no_exact_once": inspect(args.no_exact_once),
        "rwx_load": inspect(rwx_path),
        "skip_child_reset": inspect(args.skip_child_reset),
        "reuse_parent_template": inspect(args.reuse_parent_template),
    }
    require(not valid["errors"], f"valid target rejected: {valid['errors']}")
    require(not second["errors"],
            f"second valid target rejected: {second['errors']}")
    require(valid["sha256"] == second["sha256"],
            "valid target build is not deterministic")

    expected = {
        "unpatched": {"TEMPLATE_PATCH_DISABLED"},
        "wrong_offset": {"PUBLISH_OFFSET_NOT_24"},
        "wrong_image": {"MAIN_IMAGE_LOCATOR_NOT_USED"},
        "protection_not_restored": {"RESTORE_DISABLED"},
        "conflict": {"PUBLISHER_COUNT_NOT_ONE"},
        "no_exact_once": {"PUBLISHER_COUNT_NOT_ONE"},
        "rwx_load": {"TLS_NOT_IN_RW_FILE_LOAD"},
        "skip_child_reset": {"FORK_CHILD_RESET_DISABLED"},
        "reuse_parent_template": {"INHERITED_TEMPLATE_CLEAR_DISABLED"},
    }
    for name, required_errors in expected.items():
        observed = set(mutants[name]["errors"])
        require(required_errors <= observed,
                f"{name} mutant survived: {sorted(observed)}")

    result = {
        "schema": "westlake-main-tdata-target-structural-v2",
        "status": "STRUCTURAL_PASS_RUNTIME_PENDING",
        "product_activation": False,
        "device_touched": False,
        "valid": valid,
        "deterministic_builds": 2,
        "mutants": mutants,
        "structural_mutants_killed": 9,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print("PASS target structural product-publisher mutants=9 runtime=PENDING")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
