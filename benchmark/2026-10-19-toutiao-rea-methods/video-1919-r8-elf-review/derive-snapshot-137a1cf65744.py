#!/usr/bin/env python3
# candidate-r8 exact-player import derivation (Toutiao video r7 observability).
#
# WHAT: rewrite the SINGLE UND import name "__android_log_print" in libttmplayer
# 5fba8050's .dynstr into the unique new name "__wl_ttlog_00000659", so that this
# exact player -- and nothing else -- binds the compat-exported diagnostic mirror
# instead of the system __android_log_print. The system liblog/runtime are untouched;
# no global symbol is interposed.
#
# WHY THIS IS SAFE (every precondition PROVEN at runtime; see the emitted proof JSON):
#  - Target is ONE dynsym entry: index 227, FUNC GLOBAL UND, value 0, name @file 0xa6f1.
#  - Exactly one JUMP_SLOT (0x471f88) references it; version index is 0 (no versioning).
#  - No other st_name points into [name, name+19) and the byte before it is NUL, so the
#    string is standalone -- not shared, not a tail of a longer string.
#  - A real SysV DT_HASH lookup of the name resolves to index 227; a real GNU-hash lookup
#    of the name does NOT resolve (GNU symndx 601 > 227 excludes this symbol), so the GNU
#    table need not -- and does not -- change.
#  - The new name is chosen so elf_hash(NEW) % nbucket == elf_hash(OLD) % nbucket (same
#    bucket 413/521) and SysV-lookup(NEW) on the rewritten file resolves to 227 again:
#    buckets[] and chain[] are byte-identical and every lookup still correct. NEW is
#    absent from the dynsym (unique). Equal length (19) keeps every later dynstr offset
#    stable.
#  => The ONLY bytes that change are the 17 positions where OLD and NEW actually differ
#     (OLD and NEW share the "__" prefix). The NUL terminator and all relocations --
#     including the r4-proven 105 self-relative GLES/EGL .bss cache records -- are
#     byte-for-byte identical.
#
# SCOPE: this script does ELF derivation + proof only. It does NOT build, link, or touch
# the compat library. The compat->__android_log_vprint GOT binding and the liblog
# resolution source are the build recipe's concern (owned by cx-seal) and the load
# experiment card's; they are explicitly OUT of scope here and remain unverified.
#
# This script PROVES every precondition and REJECTS (nonzero exit, no output) on any drift
# or any pre-existing output file.
import sys, os, struct, hashlib, json

IN_SHA  = "5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4"
IN_SIZE = 4662040
# Pinned after the first clean run; the sentinel is replaced with the real fixed point
# so the delivered script self-verifies its own deterministic output.
OUT_SHA = "0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471"
OLD = b"__android_log_print"
NEW = b"__wl_ttlog_00000659"
TARGET_INDEX = 227
JUMP_SLOT_VA = 0x471f88
NAME_FILE_OFF = 0xa6f1
EXPECT_CACHE_RELOCS = 105          # r4-proven GLES/EGL proc-loader cache (RELATIVE in .bss)
R_AARCH64_RELATIVE = 1027
R_AARCH64_JUMP_SLOT = 1026
STT_FUNC, STT_OBJECT, STB_GLOBAL = 2, 1, 1


def die(m):
    sys.exit("REJECT: " + m)


def elf_hash(name: bytes) -> int:
    h = 0
    for b in name:
        h = (h << 4) + b
        g = h & 0xf0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xffffffff
    return h & 0xffffffff


def gnu_hash(name: bytes) -> int:
    h = 5381
    for b in name:
        h = (h * 33 + b) & 0xffffffff
    return h


def analyze(d, want, absent):
    """Pure read. Prove the target import named `want` is the unique UND FUNC GLOBAL at
    TARGET_INDEX, prove `absent` is not present, and return structural facts + the name's
    absolute file offset. Reusable on the input (want=OLD, absent=NEW) and on the rewritten
    output (want=NEW, absent=OLD)."""
    if d[:6] != b"\x7fELF\x02\x01":
        die("not ELF64LE")
    W = lambda o: struct.unpack_from("<Q", d, o)[0]
    I = lambda o: struct.unpack_from("<I", d, o)[0]
    Hh = lambda o: struct.unpack_from("<H", d, o)[0]
    phoff, phent, phnum = W(0x20), Hh(0x36), Hh(0x38)

    def segoff(va):
        for i in range(phnum):
            ph = phoff + i * phent
            if I(ph) != 1:
                continue
            off, v, fsz = W(ph + 8), W(ph + 0x10), W(ph + 0x20)
            if v <= va < v + fsz:
                return off + (va - v)
        return None

    do = dz = 0
    for i in range(phnum):
        ph = phoff + i * phent
        if I(ph) == 2:
            do, dz = W(ph + 8), W(ph + 0x20)
            break
    if not do:
        die("no PT_DYNAMIC")
    tags = {}
    o = do
    while o + 16 <= do + dz:
        t, v = W(o), W(o + 8)
        if t == 0:
            break
        tags.setdefault(t, v)
        o += 16
    for req in (6, 5, 4, 0x6ffffef5, 0x6ffffff0):
        if req not in tags:
            die(f"missing dynamic tag {hex(req)}")
    sym_off = segoff(tags[6]); str_off = segoff(tags[5]); syment = tags.get(11, 24) or 24
    hash_off = segoff(tags[4]); gnu_off = segoff(tags[0x6ffffef5]); ver_off = segoff(tags[0x6ffffff0])
    strsz = tags.get(10)
    if None in (sym_off, str_off, hash_off, gnu_off, ver_off):
        die("a dynamic table is not inside any PT_LOAD")
    nbucket, nchain = I(hash_off), I(hash_off + 4)
    buckets_off = hash_off + 8
    chain_off = buckets_off + 4 * nbucket

    def symname(st_name):
        end = d.index(0, str_off + st_name)
        return d[str_off + st_name:end]

    def st(idx):
        b = sym_off + idx * syment
        return I(b), d[b + 4], Hh(b + 6), W(b + 8)   # st_name, st_info, st_shndx, st_value

    # --- uniqueness of `want`, absence of `absent` (complete dynstr scan over dynsym) ---
    want_idxs = [i for i in range(nchain) if symname(st(i)[0]) == want]
    absent_idxs = [i for i in range(nchain) if symname(st(i)[0]) == absent]
    if absent_idxs:
        die(f"name {absent!r} already present in dynsym at {absent_idxs}")
    if want_idxs != [TARGET_INDEX]:
        die(f"target name {want!r} not unique / wrong index: {want_idxs}")
    st_name, info, shndx, value = st(TARGET_INDEX)
    if (info >> 4) != STB_GLOBAL or (info & 0xf) != STT_FUNC or shndx != 0 or value != 0:
        die("target not FUNC GLOBAL UND value=0")
    name_abs = str_off + st_name
    if name_abs != NAME_FILE_OFF:
        die(f"name file offset {hex(name_abs)} != {hex(NAME_FILE_OFF)}")
    if d[name_abs:name_abs + len(want)] != want:
        die("target name bytes mismatch")
    if d[name_abs + len(want)] != 0:
        die("target name not NUL-terminated")
    if name_abs == 0 or d[name_abs - 1] != 0:
        die("target name is not a standalone string (no preceding NUL)")
    # no other dynsym st_name points INTO the target span (would corrupt a shared string)
    span = range(st_name, st_name + len(want))   # strtab-relative
    inter = [i for i in range(nchain) if i != TARGET_INDEX and st(i)[0] in span]
    if inter:
        die(f"shared/overlapping string reference from dynsym {inter}")

    # --- symbol version must be 0 (no versioned binding to preserve) ---
    if Hh(ver_off + TARGET_INDEX * 2) != 0:
        die("target carries a non-zero symbol version")

    # --- real SysV DT_HASH lookup must resolve `want` -> TARGET_INDEX ---
    def sysv_lookup(name):
        i = I(buckets_off + (elf_hash(name) % nbucket) * 4)
        seen = 0
        while i != 0:
            if symname(st(i)[0]) == name:
                return i
            i = I(chain_off + i * 4)
            seen += 1
            if seen > nchain:
                die("SysV chain cycle")
        return 0  # STN_UNDEF

    if sysv_lookup(want) != TARGET_INDEX:
        die("SysV hash lookup of target name does not resolve to TARGET_INDEX")
    ob = elf_hash(OLD) % nbucket
    nb = elf_hash(NEW) % nbucket
    if ob != nb:
        die(f"NEW bucket {nb} != OLD bucket {ob} (hash table would change)")

    # --- real GNU-hash lookup must NOT resolve the target (symndx excludes it) ---
    gnbuckets, symndx, maskwords, shift2 = (I(gnu_off), I(gnu_off + 4), I(gnu_off + 8), I(gnu_off + 12))
    if symndx <= TARGET_INDEX:
        die(f"GNU symndx {symndx} does not exclude target index {TARGET_INDEX}")
    bloom_off = gnu_off + 16
    gbuckets_off = bloom_off + maskwords * 8
    gchain_off = gbuckets_off + gnbuckets * 4

    def gnu_lookup(name):
        h1 = gnu_hash(name)
        word = W(bloom_off + ((h1 // 64) % maskwords) * 8)
        mask = (1 << (h1 % 64)) | (1 << ((h1 >> shift2) % 64))
        if (word & mask) != mask:
            return 0
        b = I(gbuckets_off + (h1 % gnbuckets) * 4)
        if b == 0 or b < symndx:
            return 0
        i = b
        while True:
            h2 = I(gchain_off + (i - symndx) * 4)
            if (h1 | 1) == (h2 | 1) and symname(st(i)[0]) == name:
                return i
            if h2 & 1:
                return 0
            i += 1

    if gnu_lookup(want) != 0:
        die("GNU hash unexpectedly resolves the target (GNU table would need changing)")

    # --- r4-proven cache set: RELATIVE relocs whose addend == st_value of a gl*/egl*
    #     OBJECT GLOBAL symbol defined in .bss. This is the EXACT 105 r4 converted,
    #     distinct from the full 168 bss-addend RELATIVE population. ---
    e_shoff, e_shent, e_shnum, e_shstr = W(0x28), Hh(0x3a), Hh(0x3c), Hh(0x3e)
    shstr_off = W(e_shoff + e_shstr * e_shent + 0x18)

    def secname(i):
        no = I(e_shoff + i * e_shent)
        return d[shstr_off + no:d.index(0, shstr_off + no)].decode("latin1")

    bss_lo = bss_hi = bss_idx = None
    for i in range(e_shnum):
        if I(e_shoff + i * e_shent + 4) == 8 and secname(i) == ".bss":   # SHT_NOBITS
            bss_idx = i
            bss_lo = W(e_shoff + i * e_shent + 0x10)
            bss_hi = bss_lo + W(e_shoff + i * e_shent + 0x20)
            break
    if bss_idx is None:
        die("no .bss section")
    cache_vals = set()
    for i in range(nchain):
        sn, si, sh, sv = st(i)
        if (si & 0xf) == STT_OBJECT and (si >> 4) == STB_GLOBAL and sh == bss_idx:
            if symname(sn).startswith((b"gl", b"egl")):
                cache_vals.add(sv)

    jump = []
    rel_total = cache_relocs = bss_addend_relatives = 0
    for base_tag, sz_tag in ((23, 2), (7, 8)):   # DT_JMPREL/DT_PLTRELSZ, DT_RELA/DT_RELASZ
        if base_tag not in tags:
            continue
        off = segoff(tags[base_tag]); sz = tags[sz_tag]
        for i in range(sz // 24):
            r = off + i * 24
            r_off, r_info, r_add = W(r), W(r + 8), W(r + 16)
            rt, rs = r_info & 0xffffffff, r_info >> 32
            if rt == R_AARCH64_JUMP_SLOT and rs == TARGET_INDEX:
                jump.append(r_off)
            if rt == R_AARCH64_RELATIVE:
                rel_total += 1
                if bss_lo is not None and bss_lo <= r_add < bss_hi:
                    bss_addend_relatives += 1
                    if r_add in cache_vals:
                        cache_relocs += 1
    if jump != [JUMP_SLOT_VA]:
        die(f"JUMP_SLOT set {[hex(x) for x in jump]} != [{hex(JUMP_SLOT_VA)}]")
    if cache_relocs != EXPECT_CACHE_RELOCS:
        die(f"r4-proven cache relocs {cache_relocs} != {EXPECT_CACHE_RELOCS}")

    facts = dict(
        size=len(d), nbucket=nbucket, nchain=nchain, target_index=TARGET_INDEX,
        name_file_off=hex(name_abs), strsz=strsz, versym=0, gnu_symndx=symndx,
        sysv_bucket=ob, sysv_lookup_index=TARGET_INDEX, gnu_lookup_index=0,
        jump_slot=hex(JUMP_SLOT_VA), relative_total=rel_total,
        bss_addend_relatives=bss_addend_relatives, cache_relocs=cache_relocs,
        cache_symbol_count=len(cache_vals),
        elf_hash_old=hex(elf_hash(OLD)), elf_hash_new=hex(elf_hash(NEW)),
        gnu_hash_target=hex(gnu_hash(want)))
    return facts, name_abs


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: derive_ttmplayer_logmirror.py <in player.so> <out player.so> [proof.json]")
    src, dst = sys.argv[1], sys.argv[2]
    proof_path = sys.argv[3] if len(sys.argv) > 3 else None
    if os.path.exists(dst):
        die(f"output path already exists, refusing to overwrite: {dst}")
    if proof_path and os.path.exists(proof_path):
        die(f"proof path already exists, refusing to overwrite: {proof_path}")
    orig = open(src, "rb").read()
    if len(orig) != IN_SIZE:
        die(f"input size {len(orig)} != {IN_SIZE}")
    if hashlib.sha256(orig).hexdigest() != IN_SHA:
        die("input SHA drift")

    facts_in, name_abs = analyze(orig, OLD, NEW)

    d = bytearray(orig)
    d[name_abs:name_abs + len(OLD)] = NEW
    if d[name_abs + len(OLD)] != 0:
        die("NUL terminator overwritten")
    # byte diff must equal EXACTLY the positions where OLD and NEW differ (the shared
    # "__" prefix bytes are unchanged, so this is 17 positions, not 19).
    expected = [name_abs + k for k in range(len(OLD)) if OLD[k] != NEW[k]]
    diff = [k for k in range(IN_SIZE) if d[k] != orig[k]]
    if diff != expected:
        die(f"byte diff {diff} != the {len(expected)} actually-differing name bytes {expected}")

    facts_out, name_abs_out = analyze(bytes(d), NEW, OLD)
    for k in ("nbucket", "nchain", "sysv_bucket", "jump_slot", "relative_total",
              "bss_addend_relatives", "cache_relocs", "gnu_symndx", "versym",
              "sysv_lookup_index", "gnu_lookup_index", "name_file_off", "strsz"):
        if facts_out[k] != facts_in[k]:
            die(f"post-rewrite structural drift in {k}: {facts_in[k]} -> {facts_out[k]}")

    out_sha = hashlib.sha256(d).hexdigest()
    if OUT_SHA != "__PINNED_AFTER_FIRST_RUN__" and out_sha != OUT_SHA:
        die(f"output SHA {out_sha} != pinned {OUT_SHA}")

    open(dst, "wb").write(d)
    receipt = dict(
        schema="candidate-r8-import-derivation/v2",
        tool=dict(name="derive_ttmplayer_logmirror.py",
                  pinned_output=(OUT_SHA != "__PINNED_AFTER_FIRST_RUN__")),
        input=dict(path=src, sha256=IN_SHA, size=IN_SIZE),
        output=dict(path=dst, sha256=out_sha, size=len(d)),
        rename=dict(old=OLD.decode(), new=NEW.decode(), length=len(OLD),
                    name_file_offset=hex(name_abs),
                    changed_positions=[hex(x) for x in expected],
                    changed_count=len(expected)),
        preserved=dict(nul_terminator=True, relocations_total_unchanged=True,
                       r4_cache_relocs=EXPECT_CACHE_RELOCS,
                       bss_addend_relatives_total=facts_in["bss_addend_relatives"],
                       hash_tables_unchanged=True, versym_unchanged=True),
        lookups=dict(sysv_old_resolves_to=facts_in["sysv_lookup_index"],
                     sysv_new_resolves_to=facts_out["sysv_lookup_index"],
                     gnu_resolves=False),
        out_of_scope=["compat->__android_log_vprint GOT binding (build recipe + card)",
                      "liblog resolution source at preload (build recipe)",
                      "video playback outcome"],
        binding_facts_input=facts_in,
        binding_facts_output=facts_out)
    text = json.dumps(receipt, indent=2)
    if proof_path:
        open(proof_path, "w").write(text + "\n")
    print(text)
    print(f"\nOK rename {OLD.decode()} -> {NEW.decode()} ({len(expected)} bytes changed)", file=sys.stderr)
    print(f"OK out={out_sha}  cache_relocs={facts_in['cache_relocs']}/{facts_in['bss_addend_relatives']} bss-addend", file=sys.stderr)


if __name__ == "__main__":
    main()
