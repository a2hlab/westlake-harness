#!/usr/bin/env python3
# candidate-r8 exact-player import derivation (Toutiao video r7 observability).
#
# WHAT: rewrite the SINGLE byte range in libttmplayer 5fba8050's .dynstr that holds
# the UNDEF import name "__android_log_print" into the unique new name
# "__wl_ttlog_00000659", so that this exact player — and nothing else — binds the
# compat-exported diagnostic mirror instead of the system __android_log_print. The
# system liblog/runtime are untouched; no global symbol is interposed.
#
# WHY THIS IS SAFE (all proven before any write; see binding-proof.json):
#  - Target is ONE dynsym entry: index 227, FUNC GLOBAL UND, value 0, name @file 0xa6f1.
#  - Exactly one JUMP_SLOT (0x471f88) references it; version index is 0 (no versioning).
#  - No other st_name points into [name, name+19] -> the string is not shared/tail-merged.
#  - GNU hash excludes 227 (symndx 601 > 227).
#  - SysV DT_HASH (nbucket 521) DOES include 227 in bucket 413. The new name is chosen so
#    elf_hash("__wl_ttlog_00000659") % 521 == 413 == elf_hash("__android_log_print") % 521,
#    so the symbol stays in the SAME bucket at the SAME dynsym index: the hash-table bytes
#    (buckets[] and chain[]) do not change and every lookup remains correct. New name is
#    absent from the dynsym (unique). Equal length (19) keeps every dynstr offset stable.
#  => The ONLY bytes that change are the 19 name bytes at [0xa6f1, 0xa704); the NUL at
#     0xa704 and all 19896 relocations (incl. the 105 self-relative GLES/EGL cache records
#     created by the r4 derivation) are byte-for-byte identical.
#
# This script PROVES every precondition and REJECTS (nonzero exit, no output) on any drift.
import sys, struct, hashlib, json

IN_SHA  = "5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4"
IN_SIZE = 4662040
OUT_SHA = "__PINNED_AFTER_FIRST_RUN__"   # replaced with the deterministic fixed point below
OLD = b"__android_log_print"
NEW = b"__wl_ttlog_00000659"
TARGET_INDEX = 227
JUMP_SLOT_VA = 0x471f88
NAME_FILE_OFF = 0xa6f1
EXPECT_SELFREL_BSS = 105          # GLES/EGL proc-loader cache (RELATIVE, addend in .bss)
R_JUMP_SLOT, R_RELATIVE = 1026, 1027
STT_FUNC, STB_GLOBAL = 2, 1

def die(m): sys.exit("REJECT: " + m)

def elf_hash(name: bytes) -> int:
    h = 0
    for b in name:
        h = (h << 4) + b
        g = h & 0xf0000000
        if g: h ^= g >> 24
        h &= ~g & 0xffffffff
    return h & 0xffffffff

def analyze(buf):
    """Return (facts dict, name_abs offset, selfrel_bss count). Pure read."""
    d = buf
    if d[:6] != b"\x7fELF\x02\x01": die("not ELF64LE")
    W = lambda o: struct.unpack_from("<Q", d, o)[0]
    I = lambda o: struct.unpack_from("<I", d, o)[0]
    Hh = lambda o: struct.unpack_from("<H", d, o)[0]
    phoff, phent, phnum = W(0x20), Hh(0x36), Hh(0x38)
    def segoff(va):
        for i in range(phnum):
            ph = phoff + i*phent
            if I(ph) != 1: continue
            off, v, fsz = W(ph+8), W(ph+0x10), W(ph+0x20)
            if v <= va < v+fsz: return off + (va - v)
        return None
    do = dz = 0
    for i in range(phnum):
        ph = phoff + i*phent
        if I(ph) == 2: do, dz = W(ph+8), W(ph+0x20); break
    tags = {}
    o = do
    while o+16 <= do+dz:
        t, v = W(o), W(o+8)
        if t == 0: break
        tags.setdefault(t, v); o += 16
    sym_off = segoff(tags[6]); str_off = segoff(tags[5]); syment = tags.get(11, 24) or 24
    hash_off = segoff(tags[4]); gnu_off = segoff(tags[0x6ffffef5]); ver_off = segoff(tags[0x6ffffff0])
    nbucket, nchain = I(hash_off), I(hash_off+4)
    buckets_off = hash_off + 8; chain_off = buckets_off + 4*nbucket
    def symname(st_name):
        end = d.index(0, str_off + st_name); return d[str_off+st_name:end]
    # unique target + absence of new name
    matches = [i for i in range(nchain) if symname(I(sym_off+i*syment)) == OLD]
    if symname(I(sym_off+TARGET_INDEX*syment)) == NEW or any(symname(I(sym_off+i*syment)) == NEW for i in range(nchain)):
        die("new name already present in dynsym")
    if matches != [TARGET_INDEX]: die(f"target name not unique / wrong index: {matches}")
    b = sym_off + TARGET_INDEX*syment
    st_name, info, shndx, value = I(b), d[b+4], Hh(b+6), W(b+8)
    if (info>>4) != STB_GLOBAL or (info&0xf) != STT_FUNC or shndx != 0 or value != 0:
        die("target not FUNC GLOBAL UND value=0")
    name_abs = str_off + st_name
    if name_abs != NAME_FILE_OFF: die(f"name file offset {hex(name_abs)} != {hex(NAME_FILE_OFF)}")
    if d[name_abs:name_abs+len(OLD)+1] != OLD + b"\x00": die("name bytes / NUL mismatch")
    # no interior/tail string sharing
    inter = [i for i in range(nchain) if i != TARGET_INDEX
             and st_name < I(sym_off+i*syment) <= st_name+len(OLD)]
    if inter: die(f"shared/tail string reference: {inter}")
    # version 0
    if Hh(ver_off + TARGET_INDEX*2) != 0: die("target carries a symbol version")
    # gnu hash excludes target
    symndx = I(gnu_off+4)
    if symndx <= TARGET_INDEX: die(f"GNU hash symndx {symndx} does not exclude target")
    # same SysV bucket, chain reachability
    ob = elf_hash(OLD) % nbucket; nb = elf_hash(NEW) % nbucket
    if ob != nb: die(f"new name bucket {nb} != old bucket {ob}")
    ci = I(buckets_off + ob*4); walk = []
    while ci != 0 and len(walk) <= nchain:
        walk.append(ci)
        if ci == TARGET_INDEX: break
        ci = I(chain_off + ci*4)
    if TARGET_INDEX not in walk: die("target not reachable via its SysV bucket chain")
    # JUMP_SLOT uniqueness + RELATIVE/self-rel-bss accounting
    # .bss va range (SHT_NOBITS named .bss)
    e_shoff, e_shentsize, e_shnum, e_shstrndx = W(0x28), Hh(0x3a), Hh(0x3c), Hh(0x3e)
    shstr_off = W(e_shoff+e_shstrndx*e_shentsize+0x18)
    def secname(i):
        no = I(e_shoff+i*e_shentsize); end = d.index(0, shstr_off+no)
        return d[shstr_off+no:end].decode("latin1")
    bss_lo = bss_hi = None
    for i in range(e_shnum):
        if struct.unpack_from("<I", d, e_shoff+i*e_shentsize+4)[0] == 8 and secname(i) == ".bss":
            bss_lo = W(e_shoff+i*e_shentsize+0x10); bss_hi = bss_lo + W(e_shoff+i*e_shentsize+0x20); break
    jump = []; relative = 0; selfrel_bss = 0
    for base_tag, sz_tag in ((23, 2), (7, 8)):
        if base_tag not in tags: continue
        off = segoff(tags[base_tag]); sz = tags[sz_tag]
        for i in range(sz//24):
            r = off+i*24; r_off, r_info, r_add = W(r), W(r+8), W(r+16)
            rt, rs = r_info & 0xffffffff, r_info >> 32
            if rt == R_JUMP_SLOT and rs == TARGET_INDEX: jump.append(r_off)
            if rt == R_RELATIVE:
                relative += 1
                if bss_lo is not None and bss_lo <= r_add < bss_hi: selfrel_bss += 1
    if jump != [JUMP_SLOT_VA]: die(f"JUMP_SLOT set {jump} != [{hex(JUMP_SLOT_VA)}]")
    if selfrel_bss != EXPECT_SELFREL_BSS:
        die(f"self-relative .bss cache relocs {selfrel_bss} != {EXPECT_SELFREL_BSS}")
    facts = dict(size=len(d), nbucket=nbucket, nchain=nchain, target_index=TARGET_INDEX,
                 name_file_off=name_abs, versym=0, gnu_symndx=symndx,
                 sysv_bucket=ob, bucket_chain=walk, jump_slot=hex(JUMP_SLOT_VA),
                 relative_total=relative, selfrel_bss=selfrel_bss,
                 elf_hash_old=hex(elf_hash(OLD)), elf_hash_new=hex(elf_hash(NEW)))
    return facts, name_abs, selfrel_bss

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: derive_ttmplayer_logmirror.py <in player.so> <out player.so> [proof.json]")
    src, dst = sys.argv[1], sys.argv[2]
    proof_path = sys.argv[3] if len(sys.argv) > 3 else None
    orig = open(src, "rb").read()
    if len(orig) != IN_SIZE: die(f"input size {len(orig)} != {IN_SIZE}")
    if hashlib.sha256(orig).hexdigest() != IN_SHA: die("input SHA drift")
    facts, name_abs, _ = analyze(orig)

    d = bytearray(orig)
    d[name_abs:name_abs+len(OLD)] = NEW                     # the ONLY write: 19 bytes
    assert d[name_abs+len(OLD)] == 0, "NUL overwritten"     # terminator intact
    # byte-level diff must equal exactly the 19 name bytes
    diff = [k for k in range(IN_SIZE) if d[k] != orig[k]]
    expected = list(range(name_abs, name_abs+len(OLD)))
    if diff != expected:
        die(f"byte diff {diff[:5]}...(n={len(diff)}) != the {len(OLD)} name bytes")
    # re-analyze output: all structural facts identical except the renamed string
    of, on_abs, _ = analyze(bytes(d))
    for k in ("nbucket", "nchain", "sysv_bucket", "bucket_chain", "jump_slot",
              "relative_total", "selfrel_bss", "gnu_symndx"):
        if of[k] != facts[k]: die(f"post-rewrite fact drift: {k}")
    out_sha = hashlib.sha256(d).hexdigest()
    if OUT_SHA != "__PINNED_AFTER_FIRST_RUN__" and out_sha != OUT_SHA:
        die(f"output SHA {out_sha} != pinned {OUT_SHA}")
    open(dst, "wb").write(d)
    receipt = dict(
        schema="candidate-r8-import-derivation/v1",
        input=dict(path=src, sha256=hashlib.sha256(orig).hexdigest(), size=IN_SIZE),
        output=dict(path=dst, sha256=out_sha, size=len(d)),
        rename=dict(old=OLD.decode(), new=NEW.decode(), length=len(OLD),
                    file_offset=hex(name_abs),
                    byte_range=[hex(name_abs), hex(name_abs+len(OLD))]),
        changed_bytes=dict(count=len(diff), ranges=[[hex(name_abs), hex(name_abs+len(OLD))]]),
        preserved=dict(nul_terminator=True, relocations_total_unchanged=True,
                       selfrel_bss_cache=EXPECT_SELFREL_BSS,
                       hash_table_unchanged=True, versym_unchanged=True),
        binding_facts=facts)
    print(json.dumps(receipt, indent=2))
    if proof_path:
        open(proof_path, "w").write(json.dumps(receipt, indent=2) + "\n")
    print(f"\nOK string-only rename complete: {OLD.decode()} -> {NEW.decode()}", file=sys.stderr)
    print(f"OK {len(diff)} bytes changed (exactly the {len(OLD)}-byte name); out={out_sha[:16]}", file=sys.stderr)

if __name__ == "__main__":
    main()
