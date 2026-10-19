#!/usr/bin/env python3
# Derive the pre-sanitized libmffmpeg.so for Toutiao video r3, reusing RouteB
# SanitizeInitArray's EXACT semantics and bytes (link_stubs_arm64.cc, sha 87a2e823,
# evidence/r2-review/link_stubs_arm64.cc lines 344-466). It is NOT a new filter:
# it computes the same kept-slots result and writes DT_INIT_ARRAYSZ = kept*8, then
# refuses unless that reduces to the single-byte 8->0 edit the loader would make.
#
# Why a file at all: libttmplayer.so DT_NEEDED libmffmpeg.so is resolved by musl's
# by-NAME path (find_library_by_name/load_library), which never runs SanitizeInitArray
# -- that only runs on ART's explicit System.loadLibrary entry (OpenNativeLibrary).
# The original's sole INIT_ARRAY slot (0x45c168) is 0 with no relocation, so musl's
# do_init_fini (no null guard, oh61 dynlink.c e50b30f2) jumps to address 0. Replacing
# the physical file with INIT_ARRAYSZ=0 makes SanitizeInitArray a no-op (kept==count
# early return) so Java-explicit opens the same real path/inode the NEEDED load uses.
#
# Reject gates (refuse, do not weaken): input SHA/size drift; packed/undecodable relocs;
# any init slot that is non-null or relocated (would drop a real constructor); output
# that differs from input by anything other than the one DT_INIT_ARRAYSZ word; output
# SHA != the pinned fixed point.
import sys, struct, hashlib

IN_SHA  = "fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9"
IN_SIZE = 4870376
OUT_SHA = "d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4"

def die(m): sys.exit("REJECT: " + m)

src, dst = sys.argv[1], sys.argv[2]
orig = open(src, "rb").read()
d = bytearray(orig)
if len(d) != IN_SIZE: die(f"input size {len(d)} != {IN_SIZE}")
got = hashlib.sha256(d).hexdigest()
if got != IN_SHA: die(f"input SHA {got} != {IN_SHA} (input drift)")
if d[:6] != b"\x7fELF\x02\x01": die("not ELF64LE")

W = lambda o: struct.unpack_from("<Q", d, o)[0]
H = lambda o: struct.unpack_from("<H", d, o)[0]
phoff, phent, phnum = W(0x20), H(0x36), H(0x38)
if phent < 56 or phnum == 0: die("bad program headers")

def seg_fileoff(va):  # map a vaddr to file offset via PT_LOAD
    for i in range(phnum):
        ph = phoff + i*phent
        if W(ph) & 0xffffffff != 1: continue      # PT_LOAD
        off, v, fsz = W(ph+8), W(ph+0x10), W(ph+0x20)
        if v <= va < v+fsz: return off + (va-v)
    return None

dyn_off = dyn_sz = 0
for i in range(phnum):
    ph = phoff + i*phent
    if W(ph) & 0xffffffff == 2:                    # PT_DYNAMIC
        dyn_off, dyn_sz = W(ph+8), W(ph+0x20); break
if dyn_sz == 0 or dyn_off + dyn_sz > len(d): die("no PT_DYNAMIC")

ia=iasz=iasz_field=rela=relasz=jmprel=pltsz=pltrel=0; packed=False
o = dyn_off
while o + 16 <= dyn_off + dyn_sz:
    tag, val = W(o), W(o+8)
    if tag == 0: break
    if   tag == 25: ia = val
    elif tag == 27: iasz = val; iasz_field = o+8   # file offset of d_val (dynamic walked by file offset)
    elif tag == 7:  rela = val
    elif tag == 8:  relasz = val
    elif tag == 23: jmprel = val
    elif tag == 2:  pltsz = val
    elif tag == 20: pltrel = val
    elif tag in (35,36,0x6000000d,0x6000000e,0x6000000f,0x60000010): packed = True
    o += 16
if packed: die("packed/undecodable relocs present -- a null-looking slot may be relocated")
if ia == 0 or iasz == 0: die("no INIT_ARRAY")
if iasz % 8: die("INIT_ARRAYSZ not 8-aligned")
ao = seg_fileoff(ia)
if ao is None or ao + iasz > len(d): die("INIT_ARRAY not in a PT_LOAD")

def reloc_val(slot_va, stored):
    for base, sz in ((rela, relasz), (jmprel if pltrel == 7 else 0, pltsz)):
        if base == 0 or sz < 24: continue
        to = seg_fileoff(base)
        if to is None or to + sz > len(d): continue
        r = 0
        while r + 24 <= sz:
            if W(to+r) == slot_va:
                t = W(to+r+8) & 0xffffffff
                return W(to+r+16) if t == 1027 else 1   # R_AARCH64_RELATIVE -> addend, else live
            r += 24
    return stored

kept = 0
for i in range(iasz // 8):
    va = ia + i*8; eff = reloc_val(va, W(ao + i*8))
    if eff not in (0, (1<<64)-1): kept += 1
if kept != 0:
    die(f"{kept} of {iasz//8} init slot(s) are live/relocated -- refusing to drop a real constructor")

# SanitizeInitArray: compact (nothing kept) and set DT_INIT_ARRAYSZ = kept*8 = 0.
# Slots are already null, so only the ARRAYSZ word changes; verify that is the sole diff.
struct.pack_into("<Q", d, iasz_field, kept*8)
diff = [i for i in range(IN_SIZE) if d[i] != orig[i]]
if diff != [iasz_field]:
    die(f"unexpected byte diff {['%#x'%x for x in diff]} (expected only DT_INIT_ARRAYSZ @ %#x)" % iasz_field)
out = hashlib.sha256(d).hexdigest()
if out != OUT_SHA: die(f"output SHA {out} != pinned {OUT_SHA}")
open(dst, "wb").write(d)
print(f"OK input={IN_SHA[:12]} size={IN_SIZE}")
print(f"OK DT_INIT_ARRAYSZ d_val @ {iasz_field:#x}: 8 -> 0 (1 byte, {iasz//8} null slot dropped)")
print(f"OK output={out}  ({dst})")
