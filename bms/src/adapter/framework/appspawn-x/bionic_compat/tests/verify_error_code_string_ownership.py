#!/usr/bin/env python3
"""Static ownership/build-order gate for AOSP libziparchive ErrorCodeString."""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys


PROJECT = pathlib.Path(__file__).resolve().parents[5]
ADAPTER = PROJECT / "adapter"
SOURCE_ROOT = ADAPTER / "framework/appspawn-x/bionic_compat/src"
REFERENCE = ADAPTER / "frozen/references/aosp-libziparchive-error"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_reference() -> None:
    expected = {
        "zip_archive.h": "e9421b4221e79f3a4daf20d80efda8fedc0a9d49ee4fd36c49a04327bad5e8cf",
        "zip_error.cpp": "299762859b4bc2feeab1dbe6788dfaede6342728d780267c2d03517129548849",
        "zip_error.h": "e7bb05a10afb39f96ff5a0db66f59041edbf48988d3a8c6ffaf2273af4eb2dba",
    }
    for name, digest in expected.items():
        path = REFERENCE / name
        require(path.is_file(), f"missing frozen reference: {path}")
        require(sha256(path) == digest, f"frozen reference drift: {path}")


def verify_no_compat_owner() -> None:
    definition = re.compile(
        r"(?:^|\n)\s*(?:extern\s+\"C\"\s+)?const\s+char\s*\*\s*"
        r"ErrorCodeString\s*\(",
        re.MULTILINE,
    )
    for name in ("misc_compat.cpp", "art_runtime_stubs.cpp", "minizip.cpp"):
        text = (SOURCE_ROOT / name).read_text(encoding="utf-8")
        require(definition.search(text) is None, f"forbidden compat owner: {name}")

    legacy = (SOURCE_ROOT / "minizip.cpp").read_text(encoding="utf-8")
    require(
        "DEPRECATED EXPERIMENTAL READER" in legacy
        and "NOT A libziparchive PRODUCT PROVIDER" in legacy,
        "legacy minizip.cpp is not explicitly quarantined",
    )


def verify_full_build(path: pathlib.Path) -> None:
    text = path.read_text(encoding="utf-8")
    zip_sources = text.index("ZIPARCHIVE_SOURCES=$(find")
    source_gate = text.index('"$ZIPARCHIVE_DIR/zip_error.cpp"', zip_sources)
    build_zip = text.index("bld ziparchive", source_gate)
    build_artbase = text.index("bld artbase", build_zip)
    require(
        zip_sources < source_gate < build_zip < build_artbase,
        f"real zip_error.cpp provider is not built before artbase: {path.name}",
    )
    require(
        re.search(
            r'\[ "\$N" = "artbase" \].*'
            r'-Wl,--no-as-needed -lziparchive -Wl,--as-needed',
            text,
        )
        is not None,
        f"artbase lacks explicit direct libziparchive edge: {path.name}",
    )
    require(
        "smoke_exact_defined ziparchive _Z15ErrorCodeStringi 1" in text,
        f"missing sole-owner smoke gate: {path.name}",
    )
    for library, symbol in (
        ("bionic_compat", "_Z15ErrorCodeStringi"),
        ("bionic_compat", "ErrorCodeString"),
        ("art_runtime_stubs", "_Z15ErrorCodeStringi"),
        ("art_runtime_stubs", "ErrorCodeString"),
    ):
        require(
            f"smoke_exact_defined {library} {symbol} 0" in text,
            f"missing negative owner gate {library}:{symbol}: {path.name}",
        )
    require(
        "smoke_needed artbase libziparchive.so" in text,
        f"missing direct-edge artifact gate: {path.name}",
    )
    require(
        "$BC_SRC/minizip.cpp" not in text,
        f"deprecated minizip entered full build: {path.name}",
    )


def verify_generation_denylist() -> None:
    generation = ADAPTER / "framework/appspawn-x/generation"
    imported = (generation / "import_inputs.sh").read_text(encoding="utf-8")
    producer = (generation / "container_build.sh").read_text(encoding="utf-8")
    verifier = (generation / "verify_generation.py").read_text(encoding="utf-8")
    admitted = imported.split("for compat_source in", 1)[1].split("do", 1)[0]
    require("minizip.cpp" not in admitted, "generation imports deprecated minizip")
    require(
        '[[ ! -e "$COMPAT_SRC/minizip.cpp" ]]' in producer,
        "generation producer lacks minizip fail-closed gate",
    )
    for token in ('"_Z15ErrorCodeStringi"', '"ErrorCodeString"', '"minizip.cpp"'):
        require(token in verifier, f"generation verifier denylist missing {token}")


def main() -> int:
    verify_reference()
    verify_no_compat_owner()
    verify_full_build(ADAPTER / "build/inner/cross_compile_arm32.sh")
    verify_full_build(ADAPTER / "build/inner/cross_compile_arm64.sh")
    verify_generation_denylist()
    print("PASS ErrorCodeString ownership reference=locked providers=1 compat=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
