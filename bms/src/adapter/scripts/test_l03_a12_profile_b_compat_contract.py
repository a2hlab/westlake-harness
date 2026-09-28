#!/usr/bin/env python3
"""Developer P/N/F tests for Profile-B sigchain and libc++ source guards."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
REWRITER_PATH = ROOT / "scripts/rewrite_sigchain_libc.py"
CROSS_PATH = ROOT / "build/inner/cross_compile_arm64.sh"
COMPAT_PATH = ROOT / "framework/appspawn-x/bionic_compat/include/libcxx_compat.h"

SPEC = importlib.util.spec_from_file_location("rewrite_sigchain_libc", REWRITER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {REWRITER_PATH}")
REWRITER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REWRITER)


def fixture(*, bionic: str = "libc.so", musl: str = "libc_musl.so") -> str:
    return f"""\
#if defined(__BIONIC__) && !defined(__LP64__)
static int unrelated_bionic_guard = 1;
#endif
template <typename T>
static void lookup_libc_symbol(T* output) {{
#if defined(__BIONIC__)
  constexpr const char* libc_name = "{bionic}";
#elif defined(__GLIBC__)
#if __GNU_LIBRARY__ != 6
#error unsupported glibc version
#endif
  constexpr const char* libc_name = "libc.so.6";
#elif defined(ANDROID_HOST_MUSL)
  constexpr const char* libc_name = "{musl}";
#else
#error unsupported libc
#endif
  (void)libc_name;
}}
"""


class SigchainSourceContractTests(unittest.TestCase):
    def test_positive_vanilla_rewrites_only_host_musl(self) -> None:
        source = fixture()
        closed, state = REWRITER.close_source(source)
        self.assertEqual(state, "rewritten_host_musl_only")
        self.assertEqual(closed.count('libc_name = "libc.so";'), 2)
        self.assertIn("unrelated_bionic_guard", closed)
        self.assertEqual(
            closed.replace('libc_name = "libc.so";', 'libc_name = "X";', 2),
            source.replace('libc_name = "libc.so";', 'libc_name = "X";', 1).replace(
                'libc_name = "libc_musl.so";', 'libc_name = "X";'
            ),
        )

    def test_positive_already_closed_is_byte_idempotent(self) -> None:
        source = fixture(musl="libc.so")
        closed, state = REWRITER.close_source(source, require_closed=True)
        self.assertEqual(state, "already_closed")
        self.assertEqual(closed, source)

    def test_negative_bionic_identity_is_independent(self) -> None:
        with self.assertRaisesRegex(REWRITER.SourceContractError, "Bionic"):
            REWRITER.close_source(fixture(bionic="libc_musl.so"))

    def test_negative_unknown_host_musl_soname(self) -> None:
        with self.assertRaisesRegex(REWRITER.SourceContractError, "ANDROID_HOST_MUSL"):
            REWRITER.close_source(fixture(musl="libc-third.so"))

    def test_failure_missing_or_duplicate_assignment_does_not_overwrite(self) -> None:
        malformed = fixture().replace(
            '  constexpr const char* libc_name = "libc_musl.so";\n', ""
        )
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "sigchain.cc"
            output_path = Path(directory) / "closed.cc"
            source_path.write_text(malformed, encoding="utf-8")
            output_path.write_text("sentinel\n", encoding="utf-8")
            with self.assertRaisesRegex(REWRITER.SourceContractError, "exactly one"):
                REWRITER.write_closed_source(source_path, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), "sentinel\n")


class CanonicalWiringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cross = CROSS_PATH.read_text(encoding="utf-8")
        cls.compat = COMPAT_PATH.read_text(encoding="utf-8")

    def test_sigchain_uses_branch_transformer_and_elf_semantic_oracle(self) -> None:
        self.assertIn("rewrite_sigchain_libc.py", self.cross)
        self.assertIn("--verify-closed", self.cross)
        self.assertIn("SIGCHAIN_ELF_OLD_LITERAL_COUNT", self.cross)
        self.assertIn("SIGCHAIN_ELF_FIXED_LITERAL_COUNT", self.cross)
        self.assertNotIn("SIGCHAIN_OLD_LITERAL_COUNT=", self.cross)
        self.assertNotIn("SIGCHAIN_FIXED_LITERAL_COUNT=", self.cross)

    def test_libcxx_capabilities_are_split(self) -> None:
        self.assertIn("BIONIC_COMPAT_LIBCXX_NATIVE_PROMOTE", self.compat)
        self.assertIn("BIONIC_COMPAT_LIBCXX_NATIVE_COMPAT", self.compat)
        self.assertIn("__has_include(<__math/traits.h>)", self.compat)
        self.assertIn("!BIONIC_COMPAT_LIBCXX_NATIVE_PROMOTE", self.compat)
        self.assertIn("!BIONIC_COMPAT_LIBCXX_NATIVE_COMPAT", self.compat)
        self.assertNotIn("#define BIONIC_COMPAT_LIBCXX_NATIVE_MATH", self.compat)


if __name__ == "__main__":
    unittest.main(verbosity=2)
