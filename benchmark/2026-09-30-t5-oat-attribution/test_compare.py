#!/usr/bin/env python3
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

import compare_oat as c
from capture_flags import at_va, read_vm_string, LIBART_SHA

HERE = Path(__file__).resolve().parent
WORKSPACES = Path(os.environ.get("WORKSPACES", HERE.parents[2]))
REF = WORKSPACES / "westlake-generation-v3a-74d1d6d4-r8b/payload/android/framework/arm64"
MANIFEST = WORKSPACES / "westlake-harness/knowledge/toolchains/boot-image-inputs.sha256"
SHA = "25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c"


class EvidenceTests(unittest.TestCase):
    def test_candidate_real_pair_not_metadata_only(self):
        candidate = WORKSPACES / "_hw248-t5/arm64"
        report = c.analyze(REF, candidate, MANIFEST)
        self.assertEqual(sum(x["equal"] is True for x in report["images"]), 9)
        self.assertTrue(all(x["equal"] for x in report["images"] if x["name"].endswith(".vdex")))
        self.assertTrue(all(not x["comparison"]["regions"]["text"]["equal"] for x in report["segments"]))
        self.assertTrue(all(x["reference_consistent"] and x["candidate_consistent"] for x in report["image_oat_checksum_pairs"]))
        primary = next(x for x in report["segments"] if x["name"] == "boot.oat")
        self.assertEqual(primary["candidate"]["sha256"], "08837079ac97bbec25a804fc1916e5973911b8dd58733a57f8e5f52d5c9da6c9")
        self.assertEqual(primary["candidate"]["header"]["checksum"], 0x0424c4ee)
        self.assertEqual(primary["comparison"]["kv_changes"]["concurrent-copying"], ["false", "true"])
        self.assertNotIn("compilation-reason", primary["candidate"]["kv"])
        self.assertEqual(sum(len(x["reference"]["dex_records"]) for x in report["segments"]), 13)
        for segment in report["segments"]:
            for a, b in zip(segment["reference"]["dex_records"], segment["candidate"]["dex_records"]):
                self.assertEqual((a["location"], a["fields"]["location_checksum"]), (b["location"], b["fields"]["location_checksum"]))
    def test_pinned_real_reference_keys_and_offsets(self):
        report = c.analyze(REF, None, MANIFEST)
        self.assertEqual(len(report["images"]), 27)
        self.assertEqual(len(report["segments"]), 9)
        primary = next(x["reference"] for x in report["segments"] if x["name"] == "boot.oat")
        self.assertEqual(primary["sha256"], SHA)
        self.assertEqual(primary["oat_offset"], 4096)
        self.assertEqual(primary["header"]["checksum"], 0xd369f830)
        self.assertEqual(primary["header"]["key_value_store_size"], 2259)
        self.assertEqual(set(primary["kv"]), {"apex-versions", "bootclasspath", "compiler-filter",
                         "concurrent-copying", "debuggable", "dex2oat-cmdline", "native-debuggable", "requires-image"})
        self.assertEqual(primary["kv"]["requires-image"], "true")
        for row in report["segments"]:
            if row["name"] != "boot.oat":
                self.assertEqual(row["reference"]["kv"], {})

    def test_self_compare_and_text_mutation(self):
        raw = (REF / "boot.oat").read_bytes()
        parsed = c.parse(raw, SHA)
        same = c.compare(raw, raw, parsed, parsed)
        self.assertFalse(same["differences_outside_header_and_kv"])
        changed = bytearray(raw)
        changed[parsed["regions"]["text"]["offset"] + 24] ^= 1
        other = c.parse(changed)
        delta = c.compare(raw, changed, parsed, other)
        self.assertEqual(delta["kv_changes"], {})
        self.assertEqual(delta["regions"]["text"]["differing_positions"], 1)
        self.assertTrue(delta["differences_outside_header_and_kv"])

    def test_adler_inverse_against_zlib(self):
        for before in [b"", bytes(range(256)) * 13, b"body with alignment changes"]:
            prior = zlib.adler32(before)
            for suffix in [b"", b"header", b"\0" * 68 + b"key\0value\0", bytes(range(256)) * 9]:
                self.assertEqual(c.undo_adler_append(zlib.adler32(suffix, prior), suffix), prior)


class RejectionTests(unittest.TestCase):
    def test_wrong_sha_and_malformed_bounds(self):
        raw = (REF / "boot.oat").read_bytes()
        with self.assertRaisesRegex(ValueError, "SHA"):
            c.parse(raw, "0" * 64)
        for offset, value in [(4096 + 64, 0xffffffff), (4096 + 24, 0xffffffff), (40, 0xfffffff0)]:
            changed = bytearray(raw)
            struct.pack_into("<I", changed, offset, value)
            with self.assertRaises(ValueError):
                c.parse(changed)

    def test_truncation_magic_and_unterminated_kv(self):
        raw = (REF / "boot.oat").read_bytes()
        for length in [0, 63, 4100]:
            with self.assertRaises(ValueError):
                c.parse(raw[:length])
        bad = bytearray(raw)
        bad[4096 + 7] = 1
        with self.assertRaises(ValueError):
            c.parse(bad)
        bad = bytearray(raw)
        bad[4096 + 68 + 2259 - 1] = 1
        with self.assertRaisesRegex(ValueError, "unterminated"):
            c.parse(bad)

    def test_missing_candidate_is_unknown_and_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            result = subprocess.run([sys.executable, str(HERE / "compare_oat.py"),
                                     "--reference", str(REF), "--manifest", str(MANIFEST),
                                     "--candidate", str(Path(tmp) / "absent"), "--out", str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 3, result.stderr)
            report = json.loads(out.read_text())
            self.assertEqual(len(report["missing_candidate"]), 27)
            self.assertTrue(all(x["equal"] is None for x in report["images"]))
            self.assertTrue(all(x["comparison"] is None for x in report["segments"]))


class FlagTests(unittest.TestCase):
    def test_actual_binary_flag_anchors(self):
        data = (REF.parents[1] / "lib64/libart.so").read_bytes()
        self.assertEqual(c.sha(data), LIBART_SHA)
        sections = c.elf_sections(data)
        # Decode only the pinned artifact. These are evidence assertions, not generic ARM emulation.
        expected = {
            0x461bb8: "20270037",  # tbnz w0,#0 -> mismatch branch, requires false
            0x76e5a4: "48008052",  # mov w8,#2 (CMS)
            0x76e5ac: "1f4000f8",  # zero default boolean fields +4..11
            0x76e5b4: "1f0c00b9",  # zero remaining boolean fields
            0x76e5b8: "080000b9",  # store collector enum
            0x810f60: "204862b8c0035fd6",  # plain reference load/ret, no read barrier/poisoning
            0x810f68: "000040b9c0035fd6",  # plain root reference load/ret
        }
        for va, hexvalue in expected.items():
            want = bytes.fromhex(hexvalue)
            self.assertEqual(at_va(data, sections, va, len(want))[1], want)
        self.assertEqual(read_vm_string(data, sections, 0x3db6bc)["value"], "libart.so")
        evidence = json.loads((HERE / "libart-evidence.json").read_text())
        for symbol in evidence["symbols"].values():
            raw = at_va(data, sections, symbol["address"], symbol["size"])[1]
            self.assertEqual(c.sha(raw), symbol["sha256"])

    def test_unknowns_not_promoted_to_build_fact(self):
        flags = {r["flag"]: r for r in json.loads((HERE / "build-flags.json").read_text())["flags"]}
        for name in ["cxx_interpreter", "tlab_build_default", "sanitizers_and_stack_overflow_gap", "optimization_level"]:
            self.assertEqual(flags[name]["status"], "unknown")
        self.assertEqual(flags["default_collector"]["t3b_setting"], "ART_DEFAULT_GC_TYPE=CMS")
        self.assertEqual(flags["native_debug_build"]["reference_value"], False)


if __name__ == "__main__":
    unittest.main()
