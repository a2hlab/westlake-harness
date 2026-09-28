#!/usr/bin/env python3
"""Dump an Android binary AndroidManifest.xml: element names + attributes.

Only what is needed to answer "what does this manifest actually declare for
android:theme" -- attribute *names* come from the string pool, but the interesting
values (@style/... references) are TYPE_REFERENCE ints, which is exactly what
ActivityInfo.theme wants, so no resources.arsc lookup is needed.
"""
import struct
import sys

RES_STRING_POOL_TYPE = 0x0001
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
RES_XML_RESOURCE_MAP_TYPE = 0x0180

TYPE_REFERENCE = 0x01
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10
TYPE_INT_HEX = 0x11
TYPE_INT_BOOLEAN = 0x12


def parse_string_pool(buf, off):
    _type, header_size, size = struct.unpack_from("<HHI", buf, off)
    string_count, _style_count, flags, strings_start, _styles_start = struct.unpack_from(
        "<IIIII", buf, off + 8)
    is_utf8 = (flags & (1 << 8)) != 0
    offsets = struct.unpack_from("<%dI" % string_count, buf, off + header_size)
    base = off + strings_start
    out = []
    for o in offsets:
        p = base + o
        if is_utf8:
            # two varint lengths (utf16 len, then utf8 byte len)
            n = buf[p]
            p += 2 if n & 0x80 else 1
            n = buf[p]
            if n & 0x80:
                n = ((n & 0x7F) << 8) | buf[p + 1]
                p += 2
            else:
                p += 1
            out.append(buf[p:p + n].decode("utf-8", "replace"))
        else:
            n = struct.unpack_from("<H", buf, p)[0]
            p += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", buf, p)[0]
                p += 2
            out.append(buf[p:p + n * 2].decode("utf-16-le", "replace"))
    return out, size


def fmt_value(data_type, data, strings):
    if data_type == TYPE_STRING:
        return strings[data] if data < len(strings) else "<str %d>" % data
    if data_type == TYPE_REFERENCE:
        return "@0x%08x" % data
    if data_type == TYPE_INT_BOOLEAN:
        return "true" if data else "false"
    if data_type == TYPE_INT_HEX:
        return "0x%x" % data
    if data_type == TYPE_INT_DEC:
        return str(data)
    return "type%d:0x%x" % (data_type, data)


def main(path, wanted=None):
    buf = open(path, "rb").read()
    strings = []
    off = 8  # skip the outer XML chunk header
    depth = 0
    while off + 8 <= len(buf):
        ctype, _hsize, csize = struct.unpack_from("<HHI", buf, off)
        if csize == 0:
            break
        if ctype == RES_STRING_POOL_TYPE:
            strings, _ = parse_string_pool(buf, off)
        elif ctype == RES_XML_START_ELEMENT_TYPE:
            p = off + 8 + 8  # chunk header + (lineNumber, comment)
            _ns, name_idx = struct.unpack_from("<iI", buf, p)
            attr_start, _attr_size, attr_count = struct.unpack_from("<HHH", buf, p + 8)
            name = strings[name_idx]
            show = wanted is None or name in wanted
            if show:
                print("%s<%s" % ("  " * depth, name))
            ap = off + 8 + 8 + attr_start
            for _ in range(attr_count):
                a_ns, a_name, a_raw = struct.unpack_from("<iii", buf, ap)
                a_type = struct.unpack_from("<B", buf, ap + 15)[0]
                a_data = struct.unpack_from("<i", buf, ap + 16)[0]
                if show:
                    ns = "android:" if a_ns >= 0 and "android" in strings[a_ns] else ""
                    print("%s    %s%s = %s" % ("  " * depth, ns, strings[a_name],
                                               fmt_value(a_type, a_data & 0xFFFFFFFF, strings)))
                ap += 20
            if show:
                print("%s  >" % ("  " * depth))
            depth += 1
        elif ctype == RES_XML_END_ELEMENT_TYPE:
            depth -= 1
        off += csize


if __name__ == "__main__":
    wanted = set(sys.argv[2:]) or None
    main(sys.argv[1], wanted)
