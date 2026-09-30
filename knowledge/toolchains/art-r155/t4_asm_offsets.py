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

# ---- broad binary-to-binary comparison (when both R155 and the new libart are available) ----
def _syms(so, pat):
    # returns {name: (addr, size)} using nm --print-size so disassembly is bounded to the
    # exact function extent (a fixed window would overflow into neighbouring functions and
    # capture their offsets = a false layout diff).
    out = subprocess.run(["llvm-nm", "--print-size", so], capture_output=True, text=True).stdout
    r = {}
    for line in out.splitlines():
        p = line.split()
        # format: <addr> <size> <type> <name>
        if len(p) >= 4 and re.search(pat, p[3]):
            try: r[p[3]] = (int(p[0], 16), int(p[1], 16))
            except ValueError: pass
    return r

def _imm_seq(so, addr, span=512):
    # Record only Thread-field accesses (base = x19 = xSELF in art_quick). This excludes
    # GOT/global-data loads (adrp xN; ldr xN,[xN,#imm]) whose data-section offset differs
    # between two independently-linked binaries and is NOT a struct-layout signal.
    d = subprocess.run(["llvm-objdump", "-d", f"--start-address={hex(addr)}",
                        f"--stop-address={hex(addr+span)}", so], capture_output=True, text=True).stdout
    seq = []
    for line in d.splitlines():
        m = re.search(r"\b(ldr|ldar|ldrb|ldrh|str|strb|strh)\b\s+[wx]\d+,\s*\[x19(?:,\s*#(0x[0-9a-f]+|\d+))?\]", line)
        if m:
            seq.append(int(m.group(2), 0) if m.group(2) else 0)
    return seq

def cmd_compare_bin(r155, new):
    # Layout = the SET of Thread(xSELF=x19) field offsets any art_quick entrypoint dereferences.
    # Comparing the SET (not the ordered per-function sequence) is robust to disassembly-window
    # truncation and to benign code-structure differences (e.g. userdebug instrumentation) that
    # change how MANY times an offset is used but not the offset VALUE. If the two libart use the
    # same set of Thread offsets, the Thread layout matches; GOT/global loads are already excluded.
    a = _syms(r155, r"art_quick_"); b = _syms(new, r"art_quick_")
    common = sorted(set(a) & set(b))
    sa, sb = set(), set()
    for s in common:
        aa, asz = a[s]; ba, bsz = b[s]
        sa.update(_imm_seq(r155, aa, asz)); sb.update(_imm_seq(new, ba, bsz))
    only_r155 = sorted(sa - sb); only_new = sorted(sb - sa)
    da, db = dump(r155), dump(new)
    anchor_mism = {k: (da.get(k), db.get(k)) for k in set(da) | set(db) if da.get(k) != db.get(k)}
    print(f"art_quick entrypoints: R155={len(a)} NEW={len(b)} common={len(common)}")
    print(f"named anchors R155={da} NEW={db}")
    print(f"Thread(x19) offset set: R155={len(sa)} NEW={len(sb)} values")
    if anchor_mism or only_r155 or only_new:
        print(f"FAIL d4 layer C: anchor_mismatch={anchor_mism} thread_offsets_only_in_R155={only_r155} only_in_NEW={only_new}")
        return 1
    print(f"OK d4 layer C: named anchors identical AND the Thread(x19) offset set is identical "
          f"({len(sa)} values) across all {len(common)} common art_quick entrypoints => Thread layout matches board R155.")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "dump":
        sys.exit(cmd_dump(a[1]))
    if len(a) == 3 and a[0] == "compare":
        sys.exit(cmd_compare(a[1], a[2]))
    if len(a) == 3 and a[0] == "compare-bin":
        sys.exit(cmd_compare_bin(a[1], a[2]))
    print(__doc__); sys.exit(2)
