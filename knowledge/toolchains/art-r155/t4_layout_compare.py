#!/usr/bin/env python3
"""T4 layout gate — compare a newly-built libart (T3) against the board R155 libart.

Finding (offline survey of the R155 libart.so, sha 59e1bb45):
  - The .so has a full .symtab (17566 syms) BUT its DWARF is minimal (only musl crt CUs;
    0 mirror types) and the mirror accessors are inlined, and there is no
    CheckAsmSupportOffsetsAndSizes symbol. => per-field mirror OFFSETS are NOT directly
    extractable from the R155 binary.
  - What IS binary-extractable (non-circular ground truth): the version constants via
    named symbols ImageHeader::kImageVersion (=108) and the OatHeader oat version (=230),
    read from .rodata.

Therefore the layout gate has two layers:
  A. BINARY cross-check (this script, runnable now against R155 and later against the new
     libart.so): kImageVersion and kOatVersion must be byte-identical between the two .so.
     This catches an image/oat FORMAT-version drift directly against the board binary.
  B. SOURCE offsetof/sizeof compare (needs T3's ART tree): the full mirror(6 classes)+
     Thread + ImageHeader/OatHeader field layout is compared by running ART's own
     cpp-define-generator (or a offsetof dumper) on BOTH the R155 source reconstruction
     (r1 + this dir's `series`) and T3's tree, and diffing. The R155 reconstruction is the
     authoritative source per T1 (it reproduces art-hanbin byte-for-byte); layer A pins the
     format versions to the actual board binary so B is not purely self-referential.

Usage:
  t4_layout_compare.py versions <libart.so>                 # print kImageVersion/kOatVersion
  t4_layout_compare.py compare  <r155-libart.so> <new-libart.so>   # gate: versions must match
"""
import sys, re, subprocess, pathlib, json

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = HERE / "r155-expected-layout.json"

def _sym_vaddr(so, sym_re):
    out = subprocess.run(["llvm-nm", so], capture_output=True, text=True).stdout
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 3 and re.search(sym_re, p[2]):
            return int(p[0], 16)
    return None

def _read_vaddr(so, vaddr, n):
    data = pathlib.Path(so).read_bytes()
    secs = subprocess.run(["llvm-readelf", "-S", so], capture_output=True, text=True).stdout
    for m in re.finditer(r"\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)", secs):
        addr, off, size = int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)
        if addr and addr <= vaddr < addr + size:
            fo = off + (vaddr - addr)
            return data[fo:fo + n]
    return None

def versions(so):
    # ImageHeader magic 'art\n'+version and OatHeader magic 'oat\n'+version are stored as
    # constants in the binary (image.cc kImageMagic/kImageVersion, oat.cc kOatMagic/kOatVersion).
    # Scanning the magic+version byte pattern is robust (the mirror accessors are inlined and
    # there is no usable DWARF, so this is the reliable binary-extractable ground truth).
    data = pathlib.Path(so).read_bytes()
    out = {}
    mi = re.search(rb"art\n(\d\d\d)\x00", data)
    if mi:
        out["kImageVersion"] = mi.group(1).decode()
    mo = re.search(rb"oat\n(\d\d\d)\x00", data)
    if mo:
        out["kOatVersion"] = mo.group(1).decode()
    # cross-check kImageVersion against its named symbol .rodata bytes when present
    va = _sym_vaddr(so, r"ImageHeader13kImageVersionE$")
    if va:
        b = _read_vaddr(so, va, 4)
        if b:
            out["kImageVersion_symbol"] = b.split(b"\x00", 1)[0].decode(errors="replace")
    return out

def cmd_versions(so):
    v = versions(so)
    print(json.dumps(v, indent=2))
    return 0

def cmd_compare(r155, new):
    a, b = versions(r155), versions(new)
    mism = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}
    print(f"R155={a}\nNEW ={b}")
    if mism:
        print(f"FAIL d4 (binary version cross-check): mismatches={mism}")
        return 1
    print("OK d4 layer A (binary): kImageVersion/kOatVersion match the R155 board libart.")
    print("NOTE: run layer B (source offsetof via cpp-define-generator on r1+series vs T3 tree) "
          "for the full mirror/Thread/header field diff once T3 delivers its ART tree.")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "versions":
        sys.exit(cmd_versions(a[1]))
    if len(a) == 3 and a[0] == "compare":
        sys.exit(cmd_compare(a[1], a[2]))
    print(__doc__); sys.exit(2)
