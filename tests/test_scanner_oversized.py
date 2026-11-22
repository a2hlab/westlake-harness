from __future__ import annotations

import io
import struct
import unittest
import zipfile
from unittest import mock

from westlake_gap import gapmap, scanner


def tiny_elf(soname: str, needed: list[str]) -> bytes:
    """A 64-bit little-endian ELF with one PT_LOAD over the file and a PT_DYNAMIC naming SONAME and
    DT_NEEDED; addresses equal file offsets."""
    strings = b"\0"
    offsets = {}
    for name in [soname, *needed]:
        offsets[name] = len(strings)
        strings += name.encode() + b"\0"
    phoff, phnum = 64, 2
    dynamic_offset = phoff + 56 * phnum
    entries = [(1, offsets[name]) for name in needed] + [(14, offsets[soname])]
    dynamic_size = 16 * (len(entries) + 2)
    strtab = dynamic_offset + dynamic_size
    entries += [(5, strtab), (0, 0)]
    size = strtab + len(strings)
    header = (b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
              + struct.pack("<HHIQQQIHHHHHH", 3, 183, 1, 0, phoff, 0, 0, 64, 56, phnum, 64, 0, 0))
    program = (struct.pack("<IIQQQQQQ", 1, 5, 0, 0, 0, size, size, 0x1000)
               + struct.pack("<IIQQQQQQ", 2, 6, dynamic_offset, dynamic_offset, dynamic_offset,
                             dynamic_size, dynamic_size, 8))
    body = b"".join(struct.pack("<qQ", tag, value) for tag, value in entries)
    return header + program + body + strings


class OversizedElfTest(unittest.TestCase):
    def test_oversized_library_keeps_soname_and_needed(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("lib/arm64-v8a/libUE4.so", tiny_elf("libUE4.so", ["libc++_shared.so", "libz.so"]))
        records: list[dict] = []
        with mock.patch.object(scanner, "OVERSIZED_ELF_BYTES", 16):
            scanner._append_elf_records(zipfile.ZipFile(buffer), "base.apk!", records)
        self.assertEqual(1, len(records))
        record = records[0]
        self.assertEqual("oversized ELF entry", record["error"])
        self.assertEqual("libUE4.so", record["soname"])
        self.assertEqual(["libc++_shared.so", "libz.so"], record["needed"])

    def test_oversized_library_reaching_a_shadowed_one_is_routed(self) -> None:
        scan = {"apk": {"target_abi": "arm64-v8a"}, "inventory": {"elfs": [
            {"name": "base.apk!lib/arm64-v8a/libc++_shared.so", "abi": "arm64-v8a", "soname": "libc++_shared.so", "needed": []},
            {"name": "base.apk!lib/arm64-v8a/libUE4.so", "abi": "arm64-v8a", "error": "oversized ELF entry",
             "soname": "libUE4.so", "needed": ["libc++_shared.so"]},
        ]}}
        board = [prefix + "libc++_shared.so" for prefix in gapmap._SEARCHED_BEFORE_APP[:1]]
        shadowed, targets = gapmap.shadowed_libraries(scan, board)
        self.assertIn("libc++_shared.so", shadowed)
        self.assertIn("libUE4.so", targets)

    def test_non_elf_member_gives_no_names(self) -> None:
        self.assertIsNone(scanner._elf_dynamic_names(io.BytesIO(b"not an ELF at all" * 8)))


if __name__ == "__main__":
    unittest.main()
