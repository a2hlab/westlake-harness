#!/usr/bin/env python3
"""Use an exact baseline ELF/readelf receipt; all mutations stay in memory."""
import argparse
import hashlib
import json
import unittest
from pathlib import Path

from prepare_owner import FUNCTIONS, SLOTS, derive, extract


class OwnerBindings(unittest.TestCase):
    def test_known_baseline(self):
        self.assertEqual(extract(self.text, self.data), FUNCTIONS | SLOTS)

    def test_new_addresses_are_consumed(self):
        # Mutated text is a parser fixture, not a production ELF claim.
        new = dict(FUNCTIONS | SLOTS)
        new["oh_anw_get_oh"] += 4
        text = self.text.replace("0000000000125dc0", "0000000000125dc4")
        self.assertEqual(extract(text, self.data), new)
        for original in self.templates:
            output = derive(original, new)
            self.assertEqual(output, original.replace("0x125dc0", "0x125dc4"))

    def test_function_missing(self):
        with self.assertRaises(ValueError):
            extract(self.text.replace("oh_anw_get_oh", "not_the_getter"), self.data)

    def test_duplicate_function(self):
        line = next(x for x in self.text.splitlines() if x.rstrip().endswith(" oh_anw_get_oh"))
        with self.assertRaises(ValueError):
            extract(self.text + "\n" + line + "\n", self.data)

    def test_duplicate_slot(self):
        line = next(x for x in self.text.splitlines()
                    if "R_AARCH64_JUMP_SLOT" in x and "NativeObjectReference " in x)
        with self.assertRaises(ValueError):
            extract(self.text + "\n" + line + "\n", self.data)

    def test_wrong_relocation_kind(self):
        with self.assertRaises(ValueError):
            extract(self.text.replace("R_AARCH64_JUMP_SLOT", "R_AARCH64_RELATIVE"), self.data)

    def test_outside_function_mapping(self):
        with self.assertRaises(ValueError):
            extract(self.text.replace("0000000000125dc0", "fffffffffffffff0"), self.data)

    def test_bad_machine(self):
        data = bytearray(self.data)
        data[18:20] = b"\x3e\x00"
        with self.assertRaises(ValueError):
            extract(self.text, data)

    def test_missing_old_literal(self):
        with self.assertRaises(ValueError):
            derive(self.templates[0].replace("0x1740a0", "UNKNOWN"), FUNCTIONS | SLOTS)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--bridge", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--templates", type=Path, required=True)
    a = p.parse_args()
    rec = json.loads((a.evidence / "receipt.json").read_text())
    OwnerBindings.data = a.bridge.read_bytes()
    if hashlib.sha256(OwnerBindings.data).hexdigest() != rec["bridge_sha256"]:
        raise SystemExit("bridge evidence pin mismatch")
    OwnerBindings.text = (a.evidence / "readelf.stdout").read_text()
    OwnerBindings.templates = []
    for name in ("geometry.c", "pair.c"):
        source = (a.templates / name).read_bytes()
        if hashlib.sha256(source).hexdigest() != rec["sources"][name]["before"]:
            raise SystemExit("template evidence pin mismatch")
        OwnerBindings.templates.append(source.decode())
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(OwnerBindings)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
