#!/usr/bin/env python3
"""T4 layer C — extract ART offset immediates from a libart.so by disassembling the
art_quick_* assembly entrypoints (non-circular board ground truth).

Rationale (outer ring, 2026-09-30): the .so's inlined C++ accessors and minimal DWARF
hide the mirror/Thread field offsets, BUT the hand-written arm64 assembly entrypoints
(art_quick_*, all in .symtab) bake asm_support_gen.h offsets as `ldr/str Wn/Xn,[Xt,#imm]`
immediates. Disassembling them recovers the offsets the R155 libart was actually built
with. Compare these against T3's asm_support_gen.h; mismatches must be 0 to pass T4.

Anchors are (offset_name, entrypoint_symbol, base_reg, which) tuples derived from
runtime/arch/arm64/quick_entrypoints_arm64.S (art-r1). `which` selects the Nth
ldr/str against base_reg inside the entrypoint (0-based). A load `[Xt]` with no
displacement encodes offset 0.

Usage:
  t4_asm_offsets.py dump <libart.so>              # print name->offset table (json)
  t4_asm_offsets.py compare <libart.so> <asm_support_gen.h>   # gate vs T3's generated header
"""
import sys, re, json, subprocess, pathlib

# base_reg x19 = rSELF (Thread*) in art_quick entrypoints on arm64.
ANCHORS = [
    # name,                              entrypoint,                base,  which
    ("MIRROR_OBJECT_CLASS_OFFSET",       "art_quick_aput_obj",      "x0",  0),   # ldr w3,[x0]      -> 0
    ("MIRROR_CLASS_COMPONENT_TYPE_OFFSET","art_quick_aput_obj",     "x3",  0),   # ldr w3,[x3,#0xc] -> 0xc
    ("THREAD_CARD_TABLE_OFFSET",         "art_quick_aput_obj",      "x19", 0),   # ldr x3,[x19,#0x98]
    ("THREAD_ID_OFFSET",                 "art_quick_lock_object",   "x19", 0),   # ldr w9,[x19,#0x8]
]

def _disasm(so, sym):
    out = subprocess.run(["llvm-nm", so], capture_output=True, text=True).stdout
    addr = None
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 3 and p[2] == sym:
            addr = int(p[0], 16); break
    if addr is None:
        return None
    d = subprocess.run(["llvm-objdump", "-d",
                        f"--start-address={hex(addr)}", f"--stop-address={hex(addr+256)}", so],
                       capture_output=True, text=True).stdout
    return d

# match: ldr/str/ldar Wn|Xn, [<base>{, #imm}]
def _immediates(disasm, base):
    vals = []
    for line in disasm.splitlines():
        m = re.search(r"\b(ldr|ldar|str|strb|ldrb)\b\s+[wx]\d+,\s*\[" + re.escape(base) + r"(?:,\s*#(0x[0-9a-f]+|\d+))?\]", line)
        if m:
            vals.append(int(m.group(2), 0) if m.group(2) else 0)
    return vals

def dump(so):
    table = {}
    for name, sym, base, which in ANCHORS:
        dis = _disasm(so, sym)
        if dis is None:
            table[name] = None; continue
        vals = _immediates(dis, base)
        table[name] = vals[which] if which < len(vals) else None
    return table

def cmd_dump(so):
    print(json.dumps(dump(so), indent=2))
    return 0

def parse_asm_support_gen(path):
    text = pathlib.Path(path).read_text()
    out = {}
    for m in re.finditer(r"#define\s+([A-Z0-9_]+_OFFSET)\s+(0x[0-9a-fA-F]+|\d+)", text):
        out[m.group(1)] = int(m.group(2), 0)
    return out

def cmd_compare(so, gen_h):
    r155 = dump(so)
    new = parse_asm_support_gen(gen_h)
    mism = {}
    for name, val in r155.items():
        if val is None:
            mism[name] = ("EXTRACT_FAILED", new.get(name)); continue
        if name in new and new[name] != val:
            mism[name] = (val, new[name])
    print(f"R155(binary)={r155}")
    if mism:
        print(f"FAIL d4 layer C: mismatches={mism}")
        return 1
    print(f"OK d4 layer C: {len([v for v in r155.values() if v is not None])} anchored offsets match T3 asm_support_gen.h.")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "dump":
        sys.exit(cmd_dump(a[1]))
    if len(a) == 3 and a[0] == "compare":
        sys.exit(cmd_compare(a[1], a[2]))
    print(__doc__); sys.exit(2)
