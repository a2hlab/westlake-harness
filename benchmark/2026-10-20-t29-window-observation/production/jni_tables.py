"""Read the two exact bridge JNI tables, including their RELATIVE relocations."""
import re
import struct

TABLES = {
    "_ZN7android12_GLOBAL__N_122kSurfaceTextureMethodsE": 12,
    "_ZN7android12_GLOBAL__N_119kTextureViewMethodsE": 4,
}


def inspect(data, symbols):
    if data[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("JNI input not ELF64 LE")
    if struct.unpack_from("<HH", data, 16) != (3, 183):
        raise ValueError("JNI input not AArch64 ET_DYN")
    poff = struct.unpack_from("<Q", data, 32)[0]
    psz, pn = struct.unpack_from("<HH", data, 54)
    soff = struct.unpack_from("<Q", data, 40)[0]
    ssz, sn = struct.unpack_from("<HH", data, 58)
    if psz != 56 or ssz != 64 or not pn or not sn:
        raise ValueError("unsupported ELF tables")
    loads = [struct.unpack_from("<IIQQQQQQ", data, poff + i * psz) for i in range(pn)]
    loads = [x for x in loads if x[0] == 1]
    def read(va, n):
        hits = [x for x in loads if va >= x[3] and va + n <= x[3] + x[5]]
        if len(hits) != 1:
            raise ValueError("JNI pointer not unique file-backed PT_LOAD")
        off = hits[0][2] + va - hits[0][3]
        if off + n > len(data):
            raise ValueError("JNI data truncated")
        return data[off:off+n]
    relocs = {}
    for i in range(sn):
        s = struct.unpack_from("<IIQQQQIIQQ", data, soff + i * ssz)
        if s[1] != 4:
            continue
        if s[9] != 24 or s[5] % 24 or s[4] + s[5] > len(data):
            raise ValueError("invalid RELA table")
        for off in range(s[4], s[4] + s[5], 24):
            dest, info, addend = struct.unpack_from("<QQq", data, off)
            if dest in relocs:
                raise ValueError("ambiguous relocation")
            relocs[dest] = (info, addend)
    def pointer(slot):
        if slot not in relocs:
            raise ValueError("JNI pointer lacks runtime relocation")
        info, addend = relocs[slot]
        if info != 1027 or addend <= 0:
            raise ValueError("JNI pointer is not local R_AARCH64_RELATIVE")
        return addend
    def string(va):
        b = bytearray()
        for i in range(512):
            c = read(va+i, 1)
            if c == b"\0":
                return b.decode("ascii")
            b.extend(c)
        raise ValueError("unbounded JNI string")
    result = {}
    for name, count in TABLES.items():
        rows = re.findall(r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)"
                          r"\s+OBJECT\s+LOCAL\s+DEFAULT\s+\d+\s+" +
                          re.escape(name) + r"\s*$", symbols, re.M)
        if len(rows) != 1 or int(rows[0][1]) != count * 24:
            raise ValueError("missing/ambiguous/wrong-sized JNI table: " + name)
        va = int(rows[0][0], 16)
        read(va, count * 24)
        entries = []
        for i in range(count):
            nm, sig, fn = [pointer(va + 24*i + 8*j) for j in range(3)]
            if not any(x[1] & 1 and x[3] <= fn < x[3] + x[5] for x in loads):
                raise ValueError("JNI function not executable")
            names = re.findall(r"^\s*\d+:\s+" + f"{fn:016x}" +
                               r"\s+\d+\s+FUNC\s+\w+\s+\w+\s+\d+\s+(\S+)\s*$",
                               symbols, re.M)
            if not names:
                raise ValueError("JNI function has no exact symbol")
            entries.append({"name": string(nm), "signature": string(sig),
                            "function": hex(fn), "symbols": sorted(set(names))})
        if len({(e["name"], e["signature"]) for e in entries}) != count:
            raise ValueError("duplicate JNI registration")
        result[name] = {"address": hex(va), "entries": entries}
    return result


def compare(old, new):
    for name in TABLES:
        semantic = lambda rows: [(r["name"], r["signature"], r["symbols"]) for r in rows]
        if semantic(old[name]["entries"]) != semantic(new[name]["entries"]):
            raise ValueError("JNI registration/function identity changed: " + name)
