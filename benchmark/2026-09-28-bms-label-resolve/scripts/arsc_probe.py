#!/usr/bin/env python3
"""Offline probe: what Res_value type do the failing label resIds hold?

Entry #28 evidence step: wikipedia 0x7f120084 and markor 0x7f1100a1 failed with
"cannot resolve label" on the on-board resolver (3de38f09), which only accepts
RES_VALUE_TYPE_STRING (0x03). Hypothesis (outer loop): these labels are
@string references — the entry's value is itself a reference (type 0x01)
pointing at another string entry. This script walks resources.arsc with the
same layout rules as arsc_resolver.cpp and prints the value type (following
reference chains) for each resId.

Usage: arsc_probe.py <apk> <resId-hex> [<resId-hex>...]
"""
import struct
import sys
import zipfile

RES_STRING_POOL_TYPE = 0x0001
RES_TABLE_TYPE = 0x0002
RES_TABLE_PACKAGE_TYPE = 0x0200
RES_TABLE_TYPE_TYPE = 0x0201
TYPE_FLAG_SPARSE = 0x01
TYPE_FLAG_OFFSET16 = 0x02
TYPE_NAMES = {0x01: "REFERENCE", 0x02: "ATTRIBUTE", 0x03: "STRING", 0x04: "FLOAT",
              0x05: "DIMENSION", 0x06: "FRACTION", 0x10: "INT_DEC", 0x11: "INT_HEX",
              0x12: "INT_BOOLEAN"}


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


def global_pool(arsc):
    hdr = u16(arsc, 2)
    o = hdr
    while o + 8 <= len(arsc):
        ctype, chsz, csize = u16(arsc, o), u16(arsc, o + 2), u32(arsc, o + 4)
        if ctype == RES_STRING_POOL_TYPE:
            return o
        if csize < 8:
            break
        o += csize
    return None


def pool_string(arsc, pool_off, index):
    count = u32(arsc, pool_off + 8)
    flags = u32(arsc, pool_off + 16)
    str_start = u32(arsc, pool_off + 20)
    if index >= count:
        return None
    if flags & (1 << 8):  # UTF8_FLAG
        offs = pool_off + 28 + (0 if flags & 1 else count * 4)
        # style offsets follow string offsets only if styles exist; string offsets come first
        offs = pool_off + 28 + index * 4 if not (flags & 1) else None
        if offs is None:
            return None
        o = pool_off + str_start + u32(arsc, offs)
        # charLen then byteLen, each u8 or u16-with-high-bit
        cl = arsc[o]
        if cl & 0x80:
            cl = ((cl & 0x7f) << 8) | arsc[o + 1]
            o += 2
        else:
            o += 1
        bl = arsc[o]
        if bl & 0x80:
            bl = ((bl & 0x7f) << 8) | arsc[o + 1]
            o += 2
        else:
            o += 1
        return arsc[o:o + bl].decode('utf-8', 'replace')
    # UTF-16
    o = pool_off + str_start + u32(arsc, pool_off + 28 + index * 4)
    ln = u16(arsc, o)
    if ln & 0x8000:
        ln = ((ln & 0x7fff) << 16) | u16(arsc, o + 2)
        o += 4
    else:
        o += 2
    return arsc[o:o + ln * 2].decode('utf-16-le', 'replace')


def entry_offset(arsc, no, want_entry):
    """Return entry byte-offset (from entriesStart) or None, per flags encoding."""
    chsz = u16(arsc, no + 2)
    flags = arsc[no + 9]              # modern layout: res0 repurposed as flags
    entry_count = u32(arsc, no + 12)
    entries_start = u32(arsc, no + 16)
    if want_entry >= entry_count:
        return None, entries_start
    base = no + chsz                   # offsets array follows the chunk header
    if flags & TYPE_FLAG_SPARSE:
        for i in range(entry_count):
            idx, off = struct.unpack_from('<HH', arsc, base + i * 4)
            if idx == want_entry:
                return (None if off == 0xffff else off * 4), entries_start
        return None, entries_start
    if flags & TYPE_FLAG_OFFSET16:
        off = u16(arsc, base + want_entry * 2)
        return (None if off == 0xffff else off * 4), entries_start
    off = u32(arsc, base + want_entry * 4)
    return (None if off == 0xffffffff else off), entries_start


def resolve(arsc, res_id, depth=0, seen=None):
    seen = seen if seen is not None else set()
    if res_id in seen or depth > 4:
        return None
    seen.add(res_id)
    wantPkg = (res_id >> 24) & 0xff
    wantType = (res_id >> 16) & 0xff
    wantEntry = res_id & 0xffff
    hdr = u16(arsc, 2)
    o = hdr
    while o + 8 <= len(arsc):
        ctype, chsz, csize = u16(arsc, o), u16(arsc, o + 2), u32(arsc, o + 4)
        if csize < 8 or o + csize > len(arsc):
            break
        if ctype == RES_TABLE_PACKAGE_TYPE and u32(arsc, o + 8) == wantPkg:
            no = o + chsz
            end = o + csize
            while no + 8 <= end:
                nt = u16(arsc, no)
                nsz = u32(arsc, no + 4)
                if nt == RES_TABLE_TYPE_TYPE and arsc[no + 8] == wantType:
                    eoff, entries_start = entry_offset(arsc, no, wantEntry)
                    if eoff is not None:
                        ent = no + entries_start + eoff
                        esize, eflags = u16(arsc, ent), u16(arsc, ent + 2)
                        if eflags & 0x0001:
                            return ("COMPLEX", None, None)
                        vtype = arsc[ent + esize + 3]
                        vdata = u32(arsc, ent + esize + 4)
                        tname = TYPE_NAMES.get(vtype, hex(vtype))
                        s = pool_string(arsc, global_pool(arsc), vdata) if vtype == 0x03 else None
                        return (tname, vdata, s)
                no += nsz
        o += csize
    return None


def main():
    apk_path = sys.argv[1]
    arsc = zipfile.ZipFile(apk_path).read('resources.arsc')
    for arg in sys.argv[2:]:
        res_id = int(arg, 16)
        r = resolve(arsc, res_id)
        if r is None:
            print(f"{apk_path} 0x{res_id:08x}: NOT FOUND")
            continue
        tname, vdata, s = r
        line = f"{apk_path} 0x{res_id:08x}: type={tname} data={hex(vdata) if vdata is not None else ''}"
        if tname == "REFERENCE":
            nxt = resolve(arsc, vdata)
            if nxt:
                line += f" -> ref resolves to type={nxt[0]}"
                if nxt[2] is not None:
                    line += f" str={nxt[2]!r}"
        elif s is not None:
            line += f" str={s!r}"
        print(line)


if __name__ == "__main__":
    main()
