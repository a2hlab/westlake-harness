#!/usr/bin/env python3
"""Inspect ELF files for AbilityConnectionStub symbol visibility."""
import sys
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection

TARGET = "_ZTIN4OHOS5AAFwk21AbilityConnectionStubE"
VTABLE = "_ZTVN4OHOS5AAFwk21AbilityConnectionStubE"

def inspect(path):
    print(f"\n=== {path} ===")
    with open(path, "rb") as f:
        elf = ELFFile(f)
        # DT_NEEDED
        for sec in elf.iter_sections():
            if isinstance(sec, DynamicSection):
                needed = [t.needed for t in sec.iter_tags("DT_NEEDED")]
                print(f"DT_NEEDED ({len(needed)}): {needed}")
                break
        # .dynsym
        for sec in elf.iter_sections():
            if sec.name == ".dynsym":
                for sym in sec.iter_symbols():
                    n = sym.name
                    if "AbilityConnectionStub" in n or n in (TARGET, VTABLE):
                        st_type = sym["st_info"]["type"]
                        st_bind = sym["st_info"]["bind"]
                        st_vis = sym["st_other"]["visibility"]
                        shndx = sym["st_shndx"]
                        print(f"  {n:80s}  type={st_type:10s} bind={st_bind:10s} vis={st_vis:12s} shndx={shndx}")
                break

for p in sys.argv[1:]:
    inspect(p)
