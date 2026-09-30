#!/usr/bin/env python3
"""Archive selected R155 flag evidence; no loading/execution of the target library."""
import argparse
import json
from pathlib import Path
import re
import struct
import subprocess

from compare_oat import bounded, elf_sections, sha

LIBART_SHA = "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f"
SELECTORS = {
    "validate_oat": lambda n: n.startswith("art::gc::space::ImageSpace::ValidateOatFile(") and "ArrayRef" in n,
    "xgc_parse": lambda n: n.startswith("art::CmdlineType<art::XGcOption>::Parse("),
    "xgc_default": lambda n: "SaveDestination::GetOrCreateFromMap<art::XGcOption>" in n,
    "vm_library": lambda n: n.startswith("art::VMRuntime_vmLibrary("),
    "heap_reference": lambda n: n.startswith("art::gc::collector::MarkCompact::IsNullOrMarkedHeapReference("),
    "read_barrier_slow": lambda n: n == "artReadBarrierSlow",
    "root_read_barrier": lambda n: n == "artReadBarrierForRootSlow",
    "inline_cache": lambda n: n == "art_quick_update_inline_cache",
}


def at_va(data, sections, address, size):
    for sec in sections.values():
        delta = address - sec["address"]
        if sec["type"] != 8 and 0 <= delta and delta + size <= sec["size"]:
            offset = sec["offset"] + delta
            return offset, bounded(data, offset, size)
    raise ValueError(f"unmapped VA {address:x}+{size}")


def read_vm_string(data, sections, start):
    _, code = at_va(data, sections, start, 20)
    adrp, add = struct.unpack_from("<II", code, 4)
    if adrp & 0x9f00001f != 0x90000001 or add & 0xffc003ff != 0x91000021:
        raise ValueError("unexpected vmLibrary ADRP/ADD pattern")
    imm = ((adrp >> 29) & 3) | (((adrp >> 5) & 0x7ffff) << 2)
    if imm & (1 << 20):
        imm -= 1 << 21
    va = ((start + 4) & ~4095) + (imm << 12) + ((add >> 10) & 4095)
    offset, value = at_va(data, sections, va, 12)
    return dict(address=va, file_offset=offset, value=value.split(b"\0")[0].decode("ascii"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--libart", type=Path, required=True)
    p.add_argument("--llvm-bin", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = args.libart.read_bytes()
    if sha(data) != LIBART_SHA:
        p.exit(2, "R155 libart SHA mismatch\n")
    sections = elf_sections(data)
    nm = subprocess.run([str(args.llvm_bin / "llvm-nm"), "-CS", str(args.libart)],
                        check=True, capture_output=True, text=True).stdout
    symbols = []
    for line in nm.splitlines():
        m = re.fullmatch(r"([0-9a-f]+) ([0-9a-f]+) (\S) (.*)", line)
        if m:
            symbols.append((int(m[1], 16), int(m[2], 16), m[4]))
    args.out.mkdir(parents=True, exist_ok=True)
    report = dict(libart_sha256=sha(data), symbols={}, vm_library_string=None,
                  llvm_nm_sha256=sha((args.llvm_bin / "llvm-nm").read_bytes()),
                  llvm_objdump_sha256=sha((args.llvm_bin / "llvm-objdump").read_bytes()))
    for name, select in SELECTORS.items():
        matches = [row for row in symbols if select(row[2])]
        if len(matches) != 1:
            raise ValueError(f"{name}: expected one symbol, found {len(matches)}")
        address, size, symbol = matches[0]
        offset, raw = at_va(data, sections, address, size)
        asm = subprocess.run([str(args.llvm_bin / "llvm-objdump"), "-d", "--demangle",
                              f"--start-address={address}", f"--stop-address={address + size}",
                              str(args.libart)], check=True, capture_output=True, text=True).stdout
        asm = asm.replace(str(args.libart), "r155-libart.so")
        (args.out / f"libart-{name}.asm").write_text(asm)
        report["symbols"][name] = dict(symbol=symbol, address=address, size=size,
                                        file_offset=offset, sha256=sha(raw), hex=raw.hex())
        if name == "vm_library":
            report["vm_library_string"] = read_vm_string(data, sections, address)
    (args.out / "libart-evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(symbols=len(report["symbols"]), vm_library=report["vm_library_string"])))


if __name__ == "__main__":
    main()
