#!/usr/bin/env python3
# Derive libttmplayer.so for Toutiao video r4: stop the GLES/EGL proc-loader from
# writing into provider code.
#
# Mechanism (evidence): libttmplayer's GLES3/EGL-extension dispatch cache slots are
# OBJECT GLOBAL DEFAULT symbols in .bss (105 of them). The proc-loader FUN_001ddcf0
# does `p = eglGetProcAddress(name); *slot = p` where &slot comes from a GOT entry
# bound by an R_AARCH64_GLOB_DAT relocation on that symbol name. OH musl do_relocs
# (dynlink.c e50b30f2 L1389) special-cases ONLY STB_LOCAL for self-binding; for a
# GLOBAL symbol it calls find_sym_by_saved_so_list, which returns the provider's
# exported FUNC (libEGL/mali) -> the GOT slot points at provider code -> the store
# faults SEGV_ACCERR (crash: pc libttmplayer 0xde714, fault 0x7d1d95e1f8 in libEGL).
#
# Fix: rewrite each such GLOB_DAT into R_AARCH64_RELATIVE with addend = the symbol's
# own st_value. musl L1452 does `*slot = base + addend`, so the slot self-binds to
# libttmplayer's own .bss cache -> the store lands in writable .bss. Provider EGL/GL
# FUNC semantics are untouched (libttmplayer still resolves the real funcs via
# eglGetProcAddress). No symbol-table reorder, no hash change, no code change, no
# page-permission change. Reuses a loader-supported relocation type only.
#
# Narrow scope: convert ONLY the GLES/EGL proc-loader cache -- a GLOB_DAT whose symbol
# is OBJECT GLOBAL, defined in .bss (writable, the store target), and named gl*/egl*.
# This deliberately excludes the 4 C++ vtables (_ZTVN6vcloud8ttplayer...E) which are
# OBJECT GLOBAL GLOB_DAT too but live in .data.rel.ro (shndx != .bss) and must keep
# their normal interposition semantics.
#
# Reject gates: input SHA/size drift; count != expected 105; a target symbol that is
# UNDEF, not OBJECT, not STB_GLOBAL, not in .bss, or not gl*/egl*; any byte changed
# outside the converted relocations' r_info/r_addend; output SHA != the pinned fixed point.
import sys, struct, hashlib

IN_SHA  = "b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02"
IN_SIZE = 4662040
OUT_SHA = "5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4"
EXPECT_CONVERTED = 105
R_AARCH64_GLOB_DAT = 1025
R_AARCH64_RELATIVE = 1027
STT_OBJECT = 1
STB_GLOBAL = 1

def die(m): sys.exit("REJECT: " + m)
src, dst = sys.argv[1], sys.argv[2]
orig = open(src, "rb").read(); d = bytearray(orig)
if len(d) != IN_SIZE: die(f"input size {len(d)} != {IN_SIZE}")
if hashlib.sha256(d).hexdigest() != IN_SHA: die("input SHA drift")
if d[:6] != b"\x7fELF\x02\x01": die("not ELF64LE")
W=lambda o: struct.unpack_from("<Q",d,o)[0]; H=lambda o: struct.unpack_from("<H",d,o)[0]
phoff,phent,phnum=W(0x20),H(0x36),H(0x38)
def segoff(va):
    for i in range(phnum):
        ph=phoff+i*phent
        if W(ph)&0xffffffff!=1: continue
        off,v,fsz=W(ph+8),W(ph+0x10),W(ph+0x20)
        if v<=va<v+fsz: return off+(va-v)
    return None
# dynamic
do=dz=0
for i in range(phnum):
    ph=phoff+i*phent
    if W(ph)&0xffffffff==2: do,dz=segoff(W(ph+0x10)) or W(ph+8), W(ph+0x20); break
# robust: PT_DYNAMIC p_offset is a file offset already
for i in range(phnum):
    ph=phoff+i*phent
    if W(ph)&0xffffffff==2: do=W(ph+8); dz=W(ph+0x20); break
rela=relasz=relaent=symtab=syment=strtab=0
o=do
while o+16<=do+dz:
    t,v=W(o),W(o+8)
    if t==0: break
    if t==7: rela=v
    elif t==8: relasz=v
    elif t==9: relaent=v
    elif t==6: symtab=v
    elif t==11: syment=v
    elif t==5: strtab=v
    o+=16
if not(rela and relasz and symtab): die("missing DT_RELA/DT_SYMTAB")
relaent=relaent or 24; syment=syment or 24
rela_off=segoff(rela); sym_off=segoff(symtab); str_off=segoff(strtab)
if rela_off is None or sym_off is None or str_off is None: die("RELA/SYMTAB/STRTAB not in a PT_LOAD")
# Find the .bss section index from the section headers (SHT_NOBITS named ".bss").
e_shoff=W(0x28); e_shentsize=H(0x3a); e_shnum=H(0x3c); e_shstrndx=H(0x3e)
if e_shoff==0 or e_shnum==0: die("no section headers")
shstr_off=W(e_shoff+e_shstrndx*e_shentsize+0x18)
def secname(i):
    nameoff=struct.unpack_from("<I",d,e_shoff+i*e_shentsize)[0]
    end=d.index(0,shstr_off+nameoff); return d[shstr_off+nameoff:end].decode("latin1")
bss_index=None
for i in range(e_shnum):
    sh_type=struct.unpack_from("<I",d,e_shoff+i*e_shentsize+4)[0]
    if sh_type==8 and secname(i)==".bss": bss_index=i; break   # SHT_NOBITS
if bss_index is None: die("no .bss section")
def sym(idx):
    b=sym_off+idx*syment
    return (struct.unpack_from("<I",d,b)[0], d[b+4], d[b+5],
            struct.unpack_from("<H",d,b+6)[0], struct.unpack_from("<Q",d,b+8)[0])
def symname(st_name):
    end=d.index(0,str_off+st_name); return d[str_off+st_name:end].decode("latin1")
converted=0; changed=[]; skipped_vtable=0
n=relasz//relaent
for i in range(n):
    r=rela_off+i*relaent
    r_info=W(r+8); rtype=r_info & 0xffffffff; rsym=r_info>>32
    if rtype!=R_AARCH64_GLOB_DAT: continue
    st_name,st_info,st_other,st_shndx,st_value = sym(rsym)
    if (st_info&0xf)!=STT_OBJECT or (st_info>>4)!=STB_GLOBAL or st_shndx==0: continue
    name=symname(st_name)
    if st_shndx!=bss_index or not name.startswith(("gl","egl")):
        # defined OBJECT GLOBAL GLOB_DAT that is NOT the proc-loader cache (e.g. a C++
        # vtable in .data.rel.ro); leave its interposition semantics untouched.
        skipped_vtable+=1; continue
    struct.pack_into("<Q",d,r+8, R_AARCH64_RELATIVE)   # r_info: sym=0, type=RELATIVE
    struct.pack_into("<Q",d,r+16, st_value)            # r_addend = own .bss st_value
    converted+=1; changed += [r+8, r+16]
print(f"note: .bss=shndx {bss_index}; left {skipped_vtable} non-cache defined-OBJECT GLOB_DAT untouched", file=sys.stderr)
if converted!=EXPECT_CONVERTED: die(f"converted {converted} != expected {EXPECT_CONVERTED}")
# verify only the converted r_info/r_addend words differ
diff=[k for k in range(IN_SIZE) if d[k]!=orig[k]]
allowed=set()
for base in changed: allowed.update(range(base,base+8))
if set(diff)-allowed: die("unexpected byte diff outside converted relocations")
out=hashlib.sha256(d).hexdigest()
if out!=OUT_SHA: die(f"output SHA {out} != pinned {OUT_SHA}")
open(dst,"wb").write(d)
print(f"OK input={IN_SHA[:12]} size={IN_SIZE}")
print(f"OK converted {converted} GLOB_DAT->R_AARCH64_RELATIVE (self-bind addend=st_value)")
print(f"OK {len(diff)} bytes differ, all inside the {converted} rewritten relocations' r_info/r_addend fields ({converted}*16={converted*16}-byte written span)")
print(f"OK output={out}  ({dst})")
