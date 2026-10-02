import hashlib
from pathlib import Path
import struct


def sections(data):
    if data[:6] != b"\x7fELF\x02\x01":
        raise ValueError("expected little-endian ELF64")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
    offset, size, count, names_index = header[6], header[11], header[12], header[13]
    rows = [struct.unpack_from("<IIQQQQIIQQ", data, offset + index * size) for index in range(count)]
    names = data[rows[names_index][4]:rows[names_index][4] + rows[names_index][5]]
    return [{"name": names[row[0]:].split(b"\0", 1)[0].decode(), "type": row[1],
             "addr": row[3], "offset": row[4], "size": row[5], "link": row[6],
             "entry_size": row[9]} for row in rows]


def payload(data, section):
    return data[section["offset"]:section["offset"] + section["size"]]


def rodata_strings(filename):
    data = Path(filename).read_bytes()
    section = next(row for row in sections(data) if row["name"] == ".rodata")
    return {part.decode("utf-8") for part in payload(data, section).split(b"\0")
            if part and all(32 <= value < 127 for value in part)}


def normalized_relro(filename):
    data = Path(filename).read_bytes()
    rows = sections(data)
    target = next(row for row in rows if row["name"] == ".data.rel.ro")
    raw = bytearray(payload(data, target))
    symbols = {}
    for section in rows:
        if section["type"] not in (2, 11):
            continue
        table = payload(data, section)
        names = payload(data, rows[section["link"]])
        for offset in range(0, len(table), section["entry_size"]):
            name, info, other, index, address, size = struct.unpack_from("<IBBHQQ", table, offset)
            if address and (info & 15) in (1, 2):
                symbol = names[name:].split(b"\0", 1)[0].decode()
                if symbol:
                    symbols[address] = symbol
    references = {}
    for section in rows:
        if section["type"] != 4:
            continue
        table = payload(data, section)
        for offset in range(0, len(table), section["entry_size"]):
            address, info, addend = struct.unpack_from("<QQq", table, offset)
            if not target["addr"] <= address < target["addr"] + target["size"]:
                continue
            relative = address - target["addr"]
            if relative + 8 > len(raw) or (info & 0xffffffff) != 1027:
                raise ValueError("unknown readonly relocation")
            raw[relative:relative + 8] = bytes(8)
            if addend in symbols:
                meaning = {"symbol": symbols[addend]}
            else:
                destination = next((row for row in rows if row["addr"] <= addend < row["addr"] + row["size"] and row["name"] == ".rodata"), None)
                if destination is None:
                    raise ValueError("unresolved readonly target")
                position = destination["offset"] + addend - destination["addr"]
                meaning = {"string": data[position:].split(b"\0", 1)[0].decode("utf-8")}
            references[str(relative)] = meaning
    return {"size": len(raw), "nonpointer_sha256": hashlib.sha256(raw).hexdigest(), "references": references}
