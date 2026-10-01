import argparse
import hashlib
import json
from pathlib import Path
import struct


OWNER_SHA = "05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100"


def inspect(filename):
    content = Path(filename).read_bytes()
    identity = hashlib.sha256(content).hexdigest()
    if identity != OWNER_SHA:
        raise ValueError("not the read-only pulled OH OpenSLES owner")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", content)
    if header[0][:6] != b"\x7fELF\x02\x01" or header[2] != 183:
        raise ValueError("expected AArch64 little-endian ELF64")
    sections = [struct.unpack_from("<IIQQQQIIQQ", content, header[6] + index * header[11])
                for index in range(header[12])]
    names = sections[header[13]]
    section_names = content[names[4]:names[4] + names[5]]
    named = {section_names[section[0]:].split(b"\0")[0].decode(): section for section in sections}
    symbols = named[".dynsym"]
    strings_section = sections[symbols[6]]
    strings = content[strings_section[4]:strings_section[4] + strings_section[5]]

    def read_address(address, length):
        for section in sections:
            if section[1] != 8 and section[3] <= address and address + length <= section[3] + section[5]:
                return content[section[4] + address - section[3]:section[4] + address - section[3] + length]
        raise ValueError("unmapped file-backed address " + hex(address))

    exports = []
    for index in range(symbols[5] // symbols[9]):
        symbol = struct.unpack_from("<IBBHQQ", content, symbols[4] + index * symbols[9])
        name = strings[symbol[0]:].split(b"\0")[0].decode()
        binding = symbol[1] >> 4
        kind = symbol[1] & 15
        if not name or symbol[3] == 0 or binding not in [1, 2]:
            continue
        row = {"name": name, "binding": "GLOBAL" if binding == 1 else "WEAK",
               "type": "FUNC" if kind == 2 else "OBJECT" if kind == 1 else str(kind),
               "value": hex(symbol[4]), "size": symbol[5],
               "public_surface": name.startswith("SL_IID_") or name == "slCreateEngine"}
        if name.startswith("SL_IID_"):
            pointer = struct.unpack("<Q", read_address(symbol[4], 8))[0]
            row["raw_pointer"] = hex(pointer)
            row["guid_24_bytes"] = read_address(pointer, 24).hex()
        exports.append(row)
    checks = {"0x13a88": (0x13a88, "280000f9", "IObject GetState writes x8 (eight bytes) into caller's x1 output"),
              "0x14350": (0x14350, "72ffff17", "slCreateEngine tail-branches to real engine constructor at 0x14118"),
              "0x13ab0": (0x13ab0, "1f0101eb", "GetInterface compares pointer identity, not GUID contents")}
    instructions = []
    for address, (offset, expected, meaning) in checks.items():
        actual = read_address(offset, 4).hex()
        if actual != expected:
            raise ValueError("instruction pin mismatch at " + address)
        instructions.append({"address": address, "bytes_little_endian": actual, "meaning": meaning})
    return {"schema": "u10-oh-opensles-abi-evidence-v2", "owner_sha256": identity,
            "elf_machine": header[2], "exports": exports,
            "global_count": sum(row["binding"] == "GLOBAL" for row in exports),
            "weak_count": sum(row["binding"] == "WEAK" for row in exports),
            "public_count": sum(row["public_surface"] for row in exports),
            "instructions": instructions,
            "decision": "Direct Android-to-OH vtable cast rejected; IID rebind and 32/64-bit structure/output conversion required. No deployable facade in this evidence."}


def main():
    parser = argparse.ArgumentParser(description="Inspect pinned OH owner ABI before creating an Android facade")
    parser.add_argument("--owner", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.owner)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: result[name] for name in ["global_count", "weak_count", "public_count", "owner_sha256"]}))


if __name__ == "__main__":
    main()
