#!/usr/bin/env python3
# === GUARD: internal helper, do not invoke directly ===
import os as _bi_os, sys as _bi_sys
if _bi_os.environ.get("BUILD_INNER_INVOKED") != "1":
    print("[GUARD] " + _bi_os.path.basename(_bi_sys.argv[0]) + " is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc.", file=_bi_sys.stderr)
    print("[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 python3 " + _bi_os.path.basename(_bi_sys.argv[0]), file=_bi_sys.stderr)
    _bi_sys.exit(2)
# === END GUARD ===
"""Count RTTI typeinfo symbols to confirm -fno-rtti hypothesis."""
import sys
from elftools.elf.elffile import ELFFile

def count(path):
    with open(path, "rb") as f:
        elf = ELFFile(f)
        n_vtable = 0
        n_typeinfo = 0
        n_typeinfo_name = 0
        n_typeinfo_und = 0
        for sec in elf.iter_sections():
            if sec.name == ".dynsym":
                for sym in sec.iter_symbols():
                    n = sym.name
                    if not n.startswith("_Z"):
                        continue
                    shndx = sym["st_shndx"]
                    if n.startswith("_ZTV"):
                        n_vtable += 1
                    elif n.startswith("_ZTI"):
                        if shndx == "SHN_UNDEF":
                            n_typeinfo_und += 1
                        else:
                            n_typeinfo += 1
                    elif n.startswith("_ZTS"):
                        n_typeinfo_name += 1
        print(f"{path}")
        print(f"  vtable (_ZTV)     defined = {n_vtable}")
        print(f"  typeinfo (_ZTI)   defined = {n_typeinfo}")
        print(f"  typeinfo UND              = {n_typeinfo_und}")
        print(f"  typeinfo-name (_ZTS) def  = {n_typeinfo_name}")

for p in sys.argv[1:]:
    count(p)
